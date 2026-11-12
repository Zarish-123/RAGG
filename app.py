
import logging

from ingestion.pdf_loader import PDFLoader
from ingestion.chunker import Chunker
from ingestion.ocr_processor import TesseractOCRProcessor
from ingestion.image_extractor import PDFImageExtractor

from embeddings.ollama_embedder import OllamaEmbedder
from vectorstore.faiss_store import FAISSStore
from retrieval.similarity_retriever import SimilarityRetriever
from generation.ollama_llm import OllamaLLM
from pipeline.rag_pipeline import RAGPipeline


logger = logging.getLogger(__name__)


def create_rag():

    logger.info("Starting RAG pipeline initialization.")

    # Initialize OCR and image extractor
    logger.info("Initializing OCR processor and image extractor.")

    ocr_processor = TesseractOCRProcessor()
    image_extractor = PDFImageExtractor(dpi=300)

    loader = PDFLoader(
        ocr_processor=ocr_processor,
        image_extractor=image_extractor,
    )

    # PDF files
    pdf_paths = [
        "data/machine learning.pdf",
        "data/document.pdf",
    ]

    documents = []

    # Load PDF documents
    for pdf_path in pdf_paths:

        logger.info("Loading PDF: %s", pdf_path)

        loaded_documents = loader.load(pdf_path)
        documents.extend(loaded_documents)

        logger.info(
            "Extracted %d native/OCR page documents from %s.",
            len(loaded_documents),
            pdf_path,
        )

    if not documents:

        logger.error(
            "No PDF text was extracted. Check PDF paths and OCR setup."
        )

        raise ValueError(
            "No PDF text was extracted. Check PDF paths and OCR setup."
        )

    logger.info(
        "Total documents extracted: %d",
        len(documents),
    )

    # Initialize chunker
    logger.info("Starting document chunking.")

    chunker = Chunker(
        chunk_size=500,
        chunk_overlap=50,
    )

    chunks = chunker.split(documents)

    if not chunks:

        logger.error("No chunks were generated.")

        raise ValueError("No chunks were generated.")

    logger.info("Total chunks generated: %d", len(chunks))

    # Count OCR chunks
    ocr_count = sum(
        1
        for chunk in chunks
        if (
            getattr(chunk, "metadata", {}) or {}
        ).get("content_type") == "ocr"
    )

    logger.info("Total OCR chunks: %d", ocr_count)

    # Initialize embedding model
    logger.info("Initializing embedding model: nomic-embed-text.")

    embedder = OllamaEmbedder(
        model="nomic-embed-text"
    )

    # Generate embeddings
    logger.info(
        "Generating embeddings for %d chunks.",
        len(chunks),
    )

    embeddings = [
        embedder.embed(chunk.content)
        for chunk in chunks
    ]

    logger.info("Embeddings generated successfully.")

    # Initialize FAISS vector store
    logger.info("Initializing FAISS vector store.")

    vector_store = FAISSStore(
        dimension=len(embeddings[0])
    )

    vector_store.add_documents(
        chunks,
        embeddings,
    )

    logger.info("Documents added to FAISS vector store successfully.")

    # Initialize retriever
    logger.info("Initializing similarity retriever.")

    retriever = SimilarityRetriever(
        vector_store=vector_store,
        embedder=embedder,
    )

    # Initialize LLM
    logger.info("Initializing LLM: llama3.2:3b.")

    llm = OllamaLLM(
        model="llama3.2:3b"
    )

    # Create RAG pipeline
    rag = RAGPipeline(
        retriever=retriever,
        llm=llm,
    )

    # Preserve OCR chunk indices
    rag.ocr_chunk_indices = [
        index
        for index, chunk in enumerate(chunks)
        if (
            getattr(chunk, "metadata", {}) or {}
        ).get("content_type") == "ocr"
    ]

    logger.info(
        "RAG pipeline initialized successfully. "
        "Total chunks: %d | OCR chunks: %d",
        len(chunks),
        ocr_count,
    )

    return rag
