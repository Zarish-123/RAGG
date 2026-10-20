
from ingestion.pdf_loader import PDFLoader
from ingestion.chunker import Chunker
from ingestion.ocr_processor import TesseractOCRProcessor
from ingestion.image_extractor import PDFImageExtractor

from embeddings.ollama_embedder import OllamaEmbedder
from vectorstore.faiss_store import FAISSStore
from retrieval.similarity_retriever import SimilarityRetriever
from generation.ollama_llm import OllamaLLM
from pipeline.rag_pipeline import RAGPipeline


def create_rag():
    ocr_processor = TesseractOCRProcessor()
    image_extractor = PDFImageExtractor(dpi=300)

    loader = PDFLoader(
        ocr_processor=ocr_processor,
        image_extractor=image_extractor,
    )

    pdf_paths = [
        "data/machine learning.pdf",
        "data/document.pdf",
    ]

    documents = []

    for pdf_path in pdf_paths:
        print(f"\n[STARTUP] Loading PDF: {pdf_path}")

        loaded_documents = loader.load(pdf_path)
        documents.extend(loaded_documents)

        print(
            f"[STARTUP] Extracted {len(loaded_documents)} "
            f"native/OCR page documents."
        )

    if not documents:
        raise ValueError(
            "No PDF text was extracted. Check PDF paths and OCR setup."
        )

    chunker = Chunker(
        chunk_size=500,
        chunk_overlap=50,
    )

    chunks = chunker.split(documents)

    if not chunks:
        raise ValueError("No chunks were generated.")

    print(f"[STARTUP] Total chunks: {len(chunks)}")

    ocr_count = sum(
        1
        for chunk in chunks
        if (
            getattr(chunk, "metadata", {}) or {}
        ).get("content_type") == "ocr"
    )

    print(f"[STARTUP] OCR chunks: {ocr_count}")

    embedder = OllamaEmbedder(
        model="nomic-embed-text"
    )

    embeddings = [
        embedder.embed(chunk.content)
        for chunk in chunks
    ]

    vector_store = FAISSStore(
        dimension=len(embeddings[0])
    )

    vector_store.add_documents(
        chunks,
        embeddings,
    )

    retriever = SimilarityRetriever(
        vector_store=vector_store,
        embedder=embedder,
    )

    llm = OllamaLLM(
        model="llama3.2:3b"
    )

    rag = RAGPipeline(
        retriever=retriever,
        llm=llm,
    )

    # Indices refer to the same ordered chunks stored in FAISS.
    rag.ocr_chunk_indices = [
        index
        for index, chunk in enumerate(chunks)
        if (
            getattr(chunk, "metadata", {}) or {}
        ).get("content_type") == "ocr"
    ]

    return rag
