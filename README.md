# Rhino meets Claude
Connect Claude to Rhino for 3D Models 

Follow these steps to configure Claude Desktop to run Python scripts in Rhino and generate models:
- Download and install latest **Python** version from https://www.python.org/downloads/
  - You can make sure Python is installed by running the following command in a terminal:
  - `python3 --version`
- Run the following commands in a terminal:
  - `pip3 install mcp`
  - `pip3 install httpx`
- Download `rhino_mcp.py` and `rhino_bridge.py` from this repository.
- Open **Rhino**, and go **"commands -> `RunPythonScript` -> `rhino_bridge.py`**.
- Open **Claude Desktop**, go to **"Settings -> Developer -> Edit Config"**.
- Open file `claude_desktop_config.json` and copy the content of `claude_desktop_config.json` from this repository into it.
  - Make sure to fix the path to **`rhino_mcp.py`** in your **`claude_desktop_config.json`**.
- Restart claude, and instruct it to generate models in Rhino.
- Have fun!
