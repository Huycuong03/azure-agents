import logging
import os

from azure.cosmos.cosmos_client import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP
from src.utils import clean_document

logging.basicConfig(
    format="%(levelname)s: %(message)s", handlers=[logging.StreamHandler()]
)

load_dotenv()
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")

client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)  # type: ignore
app = FastAPI()
mcp = FastMCP()


@mcp.tool()
@app.get("/")
def list_databases():
    """
    List all databases in the Cosmos DB account.

    Returns:
        list: A list of database names.
    """
    databases = [db["id"] for db in client.list_databases()]
    response = JSONResponse(content={"databases": databases})
    return response


@mcp.tool()
@app.get("/{database_name}")
def list_containers(database_name: str):
    """
    List all containers in a specified database.

    Args:
        database_name (str): The name of the database.
    Returns:
        list: A list of container names.
    """
    database = client.get_database_client(database_name)
    try:
        containers = [container["id"] for container in database.list_containers()]
        response = JSONResponse({"containers": containers})
    except (CosmosResourceNotFoundError, CosmosHttpResponseError) as e:
        response = JSONResponse({"error": str(e)}, status_code=404)
    return response


@mcp.tool()
@app.post("/{database_name}/{container_name}")
def create_document(database_name: str, container_name: str, document: dict):
    """
    Create a new document in a specified container.

    Args:
        database_name (str): The name of the database.
        container_name (str): The name of the container.
        document (dict): The document data to create.
    Returns:
        status: Status message indicating success or failure.
    """
    database = client.get_database_client(database_name)
    container = database.get_container_client(container_name)
    try:
        container.create_item(document)
        response = JSONResponse({"status": "Document created successfully"})
    except (CosmosResourceNotFoundError, CosmosHttpResponseError) as e:
        response = JSONResponse({"status": str(e)}, status_code=400)
    return response


@mcp.tool()
@app.get("/{database_name}/{container_name}")
def get_all_documents(database_name: str, container_name: str):
    """
    Retrieve all documents from a specified container.

    Args:
        database_name (str): The name of the database.
        container_name (str): The name of the container.
    Returns:
        list: A list of documents in the container.
    """
    database = client.get_database_client(database_name)
    container = database.get_container_client(container_name)
    try:
        documents = list(container.read_all_items())
        documents = [clean_document(doc) for doc in documents]
        response = JSONResponse({"documents": documents})
    except (CosmosResourceNotFoundError, CosmosHttpResponseError) as e:
        response = JSONResponse({"status": str(e)}, status_code=400)
    return response


@mcp.tool()
@app.get("/{database_name}/{container_name}/{document_id}")
def find_document_by_id(database_name: str, container_name: str, document_id: str):
    """
    Find a document by its ID in a specified container.

    Args:
        database_name (str): The name of the database.
        container_name (str): The name of the container.
        document_id (str): The ID of the document to find.
    Returns:
        dict: The document data if found, otherwise an error message.
    """
    database = client.get_database_client(database_name)
    container = database.get_container_client(container_name)
    try:
        document = container.read_item(item=document_id, partition_key=document_id)
        document = clean_document(document)
        response = JSONResponse({"document": document})
    except (CosmosResourceNotFoundError, CosmosHttpResponseError) as e:
        response = JSONResponse({"error": str(e)}, status_code=404)
    return response


@mcp.tool()
@app.patch("/{database_name}/{container_name}/{document_id}")
def update_document(
    database_name: str, container_name: str, document_id: str, updates: dict
):
    """
    Update a document in a specified container.

    Args:
        database_name (str): The name of the database.
        container_name (str): The name of the container.
        document_id (str): The ID of the document to update.
        updates (dict): A dictionary of fields to update with their new values.
    Returns:
        status: Status message indicating success or failure.
    """
    database = client.get_database_client(database_name)
    container = database.get_container_client(container_name)
    try:
        container.patch_item(
            item=document_id,
            partition_key=document_id,
            patch_operations=[
                {"op": "replace", "path": f"/{key}", "value": value}
                for key, value in updates.items()
            ],
        )
        response = JSONResponse({"status": "Document updated successfully"})
    except (CosmosResourceNotFoundError, CosmosHttpResponseError) as e:
        response = JSONResponse({"status": str(e)}, status_code=400)
    return response


@mcp.tool()
@app.delete("/{database_name}/{container_name}/{document_id}")
def delete_document(database_name: str, container_name: str, document_id: str):
    """
    Delete a document from a specified container.

    Args:
        database_name (str): The name of the database.
        container_name (str): The name of the container.
        document_id (str): The ID of the document to delete.
    Returns:
        status: Status message indicating success or failure.
    """
    database = client.get_database_client(database_name)
    container = database.get_container_client(container_name)
    try:
        container.delete_item(item=document_id, partition_key=document_id)
        response = JSONResponse({"status": "Document deleted successfully"})
    except (CosmosResourceNotFoundError, CosmosHttpResponseError) as e:
        response = JSONResponse({"status": str(e)}, status_code=400)
    return response


app.mount("/mcp", mcp.streamable_http_app())
