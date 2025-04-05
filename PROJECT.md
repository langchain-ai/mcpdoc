# Project Notes: Adding New Documentation Sources

This document outlines the steps to add new `llms.txt` documentation sources to the `mcpdoc` server when it's run via the provided Docker container.

The current configuration relies on a YAML file (`mcpdoc_config.yaml`) within the Docker image to define the available documentation sources.

## Steps to Add a New Source

1.  **Edit Configuration File:**
    *   Open the `mcpdoc_config.yaml` file located in the project root (`d:/mcpdoc`).
    *   Add a new entry to the list following the existing format:
        ```yaml
        - name: YourSourceName  # Optional, but recommended
          llms_txt: https://your-domain.com/path/to/llms.txt
        ```
    *   Save the `mcpdoc_config.yaml` file.

2.  **Rebuild Docker Image:**
    *   Open a terminal in the project root directory (`d:/mcpdoc`).
    *   Run the following command to rebuild the Docker image, ensuring the updated configuration file is included:
        ```bash
        docker build -t mcpdoc-server:latest .
        ```

3.  **Restart MCP Server:**
    *   Ensure your MCP host application (e.g., VS Code with Roo Cline, Cursor, Windsurf) restarts the `langgraph-docs-mcp` server. This might happen automatically, or you may need to restart the application or manually restart the server through the MCP settings interface if available. This ensures the host uses the newly built Docker image with the updated configuration.

After these steps, the new documentation source should be available and listed when using the `list_doc_sources` tool.