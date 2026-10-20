
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from langgraph.graph import StateGraph, START, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition

from search_tools import search_web
from evaluation import evaluate_response, display_evaluation
from evaluation_logger import save_evaluation

# 1. Initialize the local LLM
llm = ChatOllama(
    model="llama3.2:3b",
    temperature=0
)


# 2. Define available tools
tools = [search_web]


# 3. Bind tools to the LLM
llm_with_tools = llm.bind_tools(tools)


# 4. Define the agent node
def call_model(state: MessagesState):

    response = llm_with_tools.invoke(
        state["messages"]
    )

    return {"messages": [response]}


# 5. Build the LangGraph workflow
builder = StateGraph(MessagesState)

builder.add_node("agent", call_model)
builder.add_node("tools", ToolNode(tools))

builder.add_edge(START, "agent")

builder.add_conditional_edges(
    "agent",
    tools_condition
)

builder.add_edge("tools", "agent")


# 6. Compile the graph
graph = builder.compile()


# 7. Define system instructions
SYSTEM_PROMPT = """
You are an AI research assistant.

When the user asks for research, recent developments,
or web sources, call the search_web tool.

Use the returned search results to answer the question.

Provide specific findings and include actual source URLs
when available in the search results.

Do not invent facts, article titles, or URLs.

If the search results are insufficient, clearly say so.
"""


# 8. Display tool calls and tool results
def display_trace(messages):

    print("\n--- TOOL CALL TRACE ---")

    tool_called = False

    for message in messages:

        # Display tools requested by the model
        tool_calls = getattr(
            message,
            "tool_calls",
            []
        )

        for tool_call in tool_calls:
            tool_called = True

            print("\nTool name:", tool_call["name"])
            print("Tool arguments:", tool_call["args"])

        # Display the actual tool output
        if message.type == "tool":

            print("\nTool result from:", message.name)

            print(
                str(message.content)[:1000]
            )

    if not tool_called:
        print("No tool call was detected in this run.")


# 9. Main application
def main():

    print("=" * 45)
    print("       AI RESEARCH AGENT")
    print("=" * 45)

    print("Model: llama3.2:3b")
    print("Available tool: search_web")
    print("Evaluation: LLM-as-a-Judge")
    print("Type 'exit' to stop.")

    while True:

        query = input("\nYou: ").strip()

        if query.lower() in {"exit", "quit"}:
            print("Agent stopped.")
            break

        if not query:
            continue

        try:

            # Run the LangGraph agent
            result = graph.invoke(
                {
                    "messages": [
                        SystemMessage(
                            content=SYSTEM_PROMPT
                        ),
                        HumanMessage(
                            content=query
                        )
                    ]
                },
                config={
                    "recursion_limit": 10
                }
            )

            messages = result["messages"]

            # Display the tool trace
            display_trace(messages)

            # Get the final assistant answer
            answer = messages[-1].content

            print("\n--- AGENT ANSWER ---")
            print(answer)

            # Collect evidence returned by search tools
            evidence_parts = [
                str(message.content)
                for message in messages
                if message.type == "tool"
            ]

            evidence = "\n\n".join(
                evidence_parts
            )

            # Evaluate the answer
            print("\nEvaluating answer with the judge model...")

            evaluation = evaluate_response(
                question=query,
                answer=str(answer),
                evidence=evidence
            )
            save_evaluation(
    question=query,
    answer=str(answer),
    evaluation=evaluation
)
            # Display evaluation metrics
            display_evaluation(evaluation)

        except Exception as error:

            print("\nAgent error:", error)


# 10. Start the application
if __name__ == "__main__":
    main()
