import streamlit.web.cli as stcli
import sys

if __name__ == '__main__':
    sys.argv = ["streamlit", "run", "dashboard.py", "--server.port", "8080", "--server.address", "0.0.0.0"]
    sys.exit(stcli.main())
