import os
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# Подключаем папку static, чтобы файлы из неё были доступны по ссылке /gui
# Если вы создали папку static и файл index.html внутри, то сайт откроется там
app.mount("/gui", StaticFiles(directory="static", html=True), name="static")

@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "Study Hub API is running",
        "mini_app_url": "/gui"
    }

# Этот блок нужен для запуска сервера
if __name__ == "__main__":
    # Railway передает порт в переменную PORT, если её нет — используем 8080
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
