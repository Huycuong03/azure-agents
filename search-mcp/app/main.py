import logging
import os

from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from azure.search.documents import SearchClient
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    format="%(levelname)s: %(message)s", handlers=[logging.StreamHandler()]
)

SEARCH_ENDPOINT = os.getenv("SEARCH_ENDPOINT")
SEARCH_KEY = os.getenv("SEARCH_KEY")

clients: dict[str, SearchClient] = {}
app = FastAPI()
mcp = FastMCP()


@mcp.tool()
@app.get("/{index_name}/{document_id}")
def find_document_by_id(index_name: str, document_id: str):
    """
    Find a document by its ID in the specified Azure Search index.

    Args:
        index_name (str): The name of the Azure Search index.
        document_id (str): The ID of the document to retrieve.
    Returns:
        dict: The retrieved document.
    """
    if index_name not in clients:
        try:
            clients[index_name] = SearchClient(
                endpoint=SEARCH_ENDPOINT,  # type: ignore
                index_name=index_name,
                credential=AzureKeyCredential(SEARCH_KEY),  # type: ignore
            )
        except HttpResponseError as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    search_client = clients[index_name]
    try:
        document = search_client.get_document(key=document_id)
        response = JSONResponse({"document": document})
    except HttpResponseError as e:
        response = JSONResponse({"error": str(e)}, status_code=404)

    return response


@mcp.tool()
@app.post("/{index_name}")
def text_search(index_name: str, search_params: dict):
    """
    Perform a text search on the specified Azure Search index.

    Args:
        index_name (str): The name of the Azure Search index.
        search_params (dict): The search parameters.

    Returns:
        list: A list of search results.
    """
    if index_name not in clients:
        try:
            clients[index_name] = SearchClient(
                endpoint=SEARCH_ENDPOINT,  # type: ignore
                index_name=index_name,
                credential=AzureKeyCredential(SEARCH_KEY),  # type: ignore
            )
        except HttpResponseError as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    search_client = clients[index_name]
    try:
        documents = search_client.search(**search_params)
        response = JSONResponse({"documents": documents})
    except HttpResponseError as e:
        response = JSONResponse({"error": str(e)}, status_code=400)

    return response
