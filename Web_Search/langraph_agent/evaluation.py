
import json
import re

from langchain_ollama import ChatOllama


# 1. Initialize the judge model
judge_llm = ChatOllama(
    model="llama3.2:3b",
    temperature=0,
    format="json"
)


# 2. Evaluate the agent's answer
def evaluate_response(
    question: str,
    answer: str,
    evidence: str
) -> dict:

    prompt = f"""
You are an impartial evaluator of an AI research assistant.

Evaluate the answer using ONLY the question, answer,
and search evidence provided below.

QUESTION:
{question}

SEARCH EVIDENCE:
{evidence if evidence.strip() else "No search evidence was captured."}

AGENT ANSWER:
{answer}

Evaluate these five criteria using integer scores from 1 to 5.

1. accuracy:
Are the claims supported by the provided evidence?

2. relevance:
Does the answer directly address the question?

3. completeness:
Does it cover the requested information?

4. groundedness:
Are the claims grounded in the supplied evidence?

5. tool_use_quality:
Were search results and source URLs used appropriately?

Scoring:
1 = Very poor
2 = Poor
3 = Acceptable
4 = Good
5 = Excellent

Do not assume a claim is true just because the agent states it.
Missing evidence should not be treated as verified information.
Give a brief reason for every score.

Return ONLY a valid JSON object in this format:
{{
  "accuracy": {{
    "score": 1,
    "reason": "Brief explanation"
  }},
  "relevance": {{
    "score": 1,
    "reason": "Brief explanation"
  }},
  "completeness": {{
    "score": 1,
    "reason": "Brief explanation"
  }},
  "groundedness": {{
    "score": 1,
    "reason": "Brief explanation"
  }},
  "tool_use_quality": {{
    "score": 1,
    "reason": "Brief explanation"
  }},
  "overall_feedback": "Most important improvement"
}}
"""

    response = judge_llm.invoke(prompt)
    raw_output = response.content

    # Parse the JSON response
    try:
        evaluation = json.loads(raw_output)

    except json.JSONDecodeError:
        # Handle extra text surrounding the JSON
        match = re.search(
            r"\{.*\}",
            raw_output,
            re.DOTALL
        )

        if not match:
            raise ValueError(
                f"Judge did not return valid JSON:\n{raw_output}"
            )

        evaluation = json.loads(match.group())

    # Validate all five metrics
    criteria = [
        "accuracy",
        "relevance",
        "completeness",
        "groundedness",
        "tool_use_quality"
    ]

    scores = []

    for criterion in criteria:
        item = evaluation.get(criterion)

        if not isinstance(item, dict):
            raise ValueError(
                f"Missing evaluation: {criterion}"
            )

        score = item.get("score")

        if (
            isinstance(score, bool)
            or not isinstance(score, int)
            or not 1 <= score <= 5
        ):
            raise ValueError(
                f"Invalid score for {criterion}: {score}"
            )

        if not isinstance(item.get("reason"), str):
            raise ValueError(
                f"Missing reason for {criterion}"
            )

        scores.append(score)

    if not isinstance(evaluation.get("overall_feedback"), str):
        raise ValueError("Missing overall_feedback")

    # Calculate average score
    evaluation["average_score"] = round(
        sum(scores) / len(scores),
        2
    )

    return evaluation


# 3. Display the evaluation
def display_evaluation(evaluation: dict):

    print("\n" + "=" * 45)
    print("       LLM-AS-A-JUDGE EVALUATION")
    print("=" * 45)

    criteria = [
        "accuracy",
        "relevance",
        "completeness",
        "groundedness",
        "tool_use_quality"
    ]

    for criterion in criteria:
        item = evaluation[criterion]

        print(
            f"\n{criterion.replace('_', ' ').title()}: "
            f"{item['score']}/5"
        )

        print("Reason:", item["reason"])

    print(
        f"\nAverage Score: "
        f"{evaluation['average_score']}/5"
    )

    print(
        "\nOverall Feedback:",
        evaluation["overall_feedback"]
    )
