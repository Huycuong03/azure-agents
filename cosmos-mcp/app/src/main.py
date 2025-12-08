import os

from azure.cosmos.aio import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from mcp.server.fastmcp import FastMCP
from src.utils import clean_document

load_dotenv()
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")

client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)  # type: ignore
api = FastAPI()
mcp = FastMCP()


@mcp.tool()
@api.get("/")
async def list_databases():
    """
    List all databases in the Cosmos DB account.

    Returns:
        list: A list of database names.
    """
    databases = [db["id"] async for db in client.list_databases()]
    return {"databases": databases}


@mcp.tool()
@api.get("/{database_name}")
async def list_containers(database_name: str):
    """
    List all containers in a specified database.

    Args:
        database_name (str): The name of the database.
    Returns:
        list: A list of container names.
    """
    try:
        database = client.get_database_client(database_name)
        containers = [container["id"] async for container in database.list_containers()]
        return {"database": database_name, "containers": containers}
    except CosmosResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CosmosHttpResponseError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@mcp.tool()
@api.post("/{database_name}/{container_name}", status_code=status.HTTP_204_NO_CONTENT)
async def create_document(database_name: str, container_name: str, document: dict):
    """
    Create a new document in a specified container.

    Args:
        database_name (str): The name of the database.
        container_name (str): The name of the container.
        document (dict): The document data to create.
    Returns:
        status: Status message indicating success or failure.
    """
    try:
        database = client.get_database_client(database_name)
        container = database.get_container_client(container_name)
        await container.create_item(document)
    except CosmosResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CosmosHttpResponseError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@mcp.tool()
@api.get("/{database_name}/{container_name}")
async def get_all_documents(database_name: str, container_name: str):
    """
    Retrieve all documents from a specified container.

    Args:
        database_name (str): The name of the database.
        container_name (str): The name of the container.
    Returns:
        list: A list of documents in the container.
    """
    try:
        database = client.get_database_client(database_name)
        container = database.get_container_client(container_name)
        documents = []
        async for doc in container.read_all_items():
            doc = clean_document(doc)
            documents.append(doc)
        return {
            "database": database_name,
            "container": container_name,
            "documents": documents,
        }
    except CosmosResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CosmosHttpResponseError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@mcp.tool()
@api.get("/{database_name}/{container_name}/{document_id}")
async def find_document_by_id(
    database_name: str, container_name: str, document_id: str
):
    """
    Find a document by its ID in a specified container.

    Args:
        database_name (str): The name of the database.
        container_name (str): The name of the container.
        document_id (str): The ID of the document to find.
    Returns:
        dict: The document data if found, otherwise an error message.
    """
    try:
        database = client.get_database_client(database_name)
        container = database.get_container_client(container_name)
        document = await container.read_item(
            item=document_id, partition_key=document_id
        )
        document = clean_document(document)
        return {
            "database": database_name,
            "container": container_name,
            "document": document,
        }
    except CosmosResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CosmosHttpResponseError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@mcp.tool()
@api.patch(
    "/{database_name}/{container_name}/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def update_document(
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
    try:
        database = client.get_database_client(database_name)
        container = database.get_container_client(container_name)
        await container.patch_item(
            item=document_id,
            partition_key=document_id,
            patch_operations=[
                {"op": "replace", "path": f"/{key}", "value": value}
                for key, value in updates.items()
            ],
        )
    except CosmosResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CosmosHttpResponseError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@mcp.tool()
@api.delete(
    "/{database_name}/{container_name}/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(database_name: str, container_name: str, document_id: str):
    """
    Delete a document from a specified container.

    Args:
        database_name (str): The name of the database.
        container_name (str): The name of the container.
        document_id (str): The ID of the document to delete.
    Returns:
        status: Status message indicating success or failure.
    """
    try:
        database = client.get_database_client(database_name)
        container = database.get_container_client(container_name)
        await container.delete_item(item=document_id, partition_key=document_id)
    except CosmosResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CosmosHttpResponseError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


app = mcp.streamable_http_app()
app.mount("/api", api)
