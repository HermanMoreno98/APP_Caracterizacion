import os
import sys

# Agregar el directorio actual al path de Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dap_automate import app

if __name__ == "__main__":
    app.run() 