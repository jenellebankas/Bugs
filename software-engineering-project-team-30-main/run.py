from app import app
import os
from config import gmaps

if __name__=="__main__":
    port = int(os.environ.get("PORT", 8500))
    app.run(host="0.0.0.0", port=port)

