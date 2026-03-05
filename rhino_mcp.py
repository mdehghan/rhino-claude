"""
RhinoMCP - All-in-One MCP Server
This script runs BOTH as an MCP server AND connects to Rhino
Eliminates the need for a separate MCP server script!

ARCHITECTURE:
- Runs as standalone Python process (launched by Claude Desktop)
- Implements MCP protocol via stdio
- Connects to Rhino via HTTP API (RhinoCompute or custom endpoint)

NOTE: This requires Rhino to expose an HTTP API. Two options:
1. Use RhinoCompute (if available)
2. Run a simple HTTP server inside Rhino (see companion script)

INSTALLATION:
1. Save this as rhino_mcp.py
2. Install dependencies: pip install mcp httpx
3. Configure Claude Desktop to run this script
4. Start the Rhino HTTP server (companion script)
"""

import asyncio
import json
import urllib.request
import sys
from typing import Any

# Check if MCP is available
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("ERROR: MCP library not installed", file=sys.stderr)
    print("Install with: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Rhino HTTP server configuration
RHINO_HOST = "localhost"
RHINO_PORT = 8080
RHINO_URL = "http://127.0.0.1:5123/run_script"


def post(op, args):
    payload = json.dumps({"args": args}).encode("utf-8")
    req = urllib.request.Request(
        RHINO_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())

# === MCP TOOL DEFINITIONS ===

# Create FastMCP server FIRST (before decorators)
mcp = FastMCP("rhino-mcp-direct")

@mcp.tool()
async def execute_python_script(script: str) -> str:
    """
    Execute custom Python script in Rhino using Rhino.Geometry as rg.
    The script you create should have a main function: def main(doc, params):.
    
    IMPORTANT PATTERNS FOR RELIABLE EXECUTION:
    1. Use getattr(doc, "ModelAbsoluteTolerance", 0.01) for tolerance
    2. Wrap collections in list() for Boolean operations (e.g., list(cutters))
    3. Convert object IDs to strings in return: ids = [str(id1), str(id2)]
    4. Use try/except around doc.Views.Redraw()
    5. Add fallback with 'or' for Boolean operations that might fail
    6. Use helper functions like box_brep() for creating geometry
    
    Example:
    import Rhino.Geometry as rg
    
    def main(doc, params):
        tol = getattr(doc, "ModelAbsoluteTolerance", 0.01)
        ids = []
        
        def box_brep(x0, y0, z0, x1, y1, z1):
            bbox = rg.BoundingBox(rg.Point3d(x0, y0, z0), rg.Point3d(x1, y1, z1))
            return rg.Box(bbox).ToBrep()
        
        def boolean_diff(a, cutters):
            # IMPORTANT: wrap as list for IEnumerable[Brep]
            res = rg.Brep.CreateBooleanDifference([a], list(cutters), tol)
            if res and len(res) > 0:
                return res[0]
            return None
        
        # Create geometry
        box = box_brep(0, 0, 0, 100, 100, 100)
        sphere = rg.Sphere(rg.Point3d(50, 50, 50), 60).ToBrep()
        
        # Boolean with fallback
        result = boolean_diff(box, [sphere]) or box
        
        # Add to document and convert ID to string
        ids.append(str(doc.Objects.AddBrep(result)))
        
        try:
            doc.Views.Redraw()
        except:
            pass
        
        return {"ok": True, "ids": ids}
    
    Args:
        script: Python code to execute (must use Rhino.Geometry as rg)
    
    """
    res = post("run_script", {
        "script": script,
        "params": {}
    })
    return str(res)


# === SERVER STARTUP ===

    

if __name__ == "__main__":
    """Run the MCP server"""
    print("Starting RhinoMCP Direct Server...", file=sys.stderr)
    print(f"Connecting to Rhino at {RHINO_HOST}:{RHINO_PORT}", file=sys.stderr)
    
    mcp.run(transport="stdio")
