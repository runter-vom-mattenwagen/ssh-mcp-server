#!/usr/bin/env python3
"""
SSH MCP Server
Provides SSH command execution capabilities via MCP protocol
"""

import json
import sys
import os
from pathlib import Path
from ssh_client import SSHClient


def send_response(response):
    """Send JSON-RPC response via stdout"""
    print(json.dumps(response), flush=True)


def handle_initialize(request):
    """Initialize handshake"""
    send_response({
        "jsonrpc": "2.0",
        "id": request.get("id"),
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "ssh-mcp-server",
                "version": "1.0.0"
            }
        }
    })


def handle_tools_list(request):
    """Return available tools"""
    tools = [
        {
            "name": "ssh_exec",
            "description": "Execute a command on a remote host via SSH",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "description": "Target host (hostname or IP)"
                    },
                    "command": {
                        "type": "string",
                        "description": "Command to execute"
                    },
                    "user": {
                        "type": "string",
                        "description": "SSH user (default: root)",
                        "default": "root"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Command timeout in seconds (default: 30)",
                        "default": 30
                    }
                },
                "required": ["host", "command"]
            }
        },
        {
            "name": "ssh_upload",
            "description": "Upload a file to remote host via SFTP",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "description": "Target host (hostname or IP)"
                    },
                    "local_path": {
                        "type": "string",
                        "description": "Local file path"
                    },
                    "remote_path": {
                        "type": "string",
                        "description": "Remote destination path"
                    },
                    "user": {
                        "type": "string",
                        "description": "SSH user (default: root)",
                        "default": "root"
                    }
                },
                "required": ["host", "local_path", "remote_path"]
            }
        },
        {
            "name": "ssh_download",
            "description": "Download a file from remote host via SFTP",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "description": "Target host (hostname or IP)"
                    },
                    "remote_path": {
                        "type": "string",
                        "description": "Remote file path"
                    },
                    "local_path": {
                        "type": "string",
                        "description": "Local destination path"
                    },
                    "user": {
                        "type": "string",
                        "description": "SSH user (default: root)",
                        "default": "root"
                    }
                },
                "required": ["host", "remote_path", "local_path"]
            }
        }
    ]
    
    send_response({
        "jsonrpc": "2.0",
        "id": request.get("id"),
        "result": {
            "tools": tools
        }
    })


def handle_tools_call(request):
    """Execute tool"""
    params = request.get("params", {})
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    
    try:
        if tool_name == "ssh_exec":
            host = arguments["host"]
            command = arguments["command"]
            user = arguments.get("user", "root")
            timeout = arguments.get("timeout", 30)
            
            ssh = SSHClient(host, user)
            stdout, stderr, exit_code = ssh.exec(command, timeout)
            ssh.disconnect()
            
            # Format output
            output = f"Exit Code: {exit_code}\n"
            if stdout:
                output += f"\nSTDOUT:\n{stdout}"
            if stderr:
                output += f"\nSTDERR:\n{stderr}"
            
            send_response({
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": output
                        }
                    ]
                }
            })
        
        elif tool_name == "ssh_upload":
            host = arguments["host"]
            local_path = os.path.expanduser(arguments["local_path"])
            remote_path = arguments["remote_path"]
            user = arguments.get("user", "root")
            
            ssh = SSHClient(host, user)
            ssh.upload(local_path, remote_path)
            ssh.disconnect()
            
            send_response({
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Successfully uploaded {local_path} to {host}:{remote_path}"
                        }
                    ]
                }
            })
        
        elif tool_name == "ssh_download":
            host = arguments["host"]
            remote_path = arguments["remote_path"]
            local_path = os.path.expanduser(arguments["local_path"])
            user = arguments.get("user", "root")
            
            ssh = SSHClient(host, user)
            ssh.download(remote_path, local_path)
            ssh.disconnect()
            
            send_response({
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Successfully downloaded {host}:{remote_path} to {local_path}"
                        }
                    ]
                }
            })
        
        else:
            send_response({
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Unknown tool: {tool_name}"
                }
            })
    
    except Exception as e:
        send_response({
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "error": {
                "code": -32000,
                "message": str(e)
            }
        })


def main():
    """Main loop - reads JSON-RPC from stdin"""
    for line in sys.stdin:
        try:
            request = json.loads(line)
            method = request.get("method")
            
            if method == "initialize":
                handle_initialize(request)
            elif method == "notifications/initialized":
                # Client confirms initialization - no response needed
                continue
            elif method == "tools/list":
                handle_tools_list(request)
            elif method == "tools/call":
                handle_tools_call(request)
            else:
                # Only send error if there's an ID (request, not notification)
                if request.get("id") is not None:
                    send_response({
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}"
                        }
                    })
        except json.JSONDecodeError:
            continue
        except Exception:
            continue


if __name__ == "__main__":
    main()
