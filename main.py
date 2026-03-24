import os
import time
import logging
from datetime import datetime
import requests

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# =========================
# 🔧 CONFIG VIA ENV
# =========================

LOGIN = os.getenv("LOGIN_WRSAT")
SENHA = os.getenv("SENHA_WRSAT")
DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH", "/home/automacao/downloads")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

# =========================
# 📝 LOG
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def log(msg):
    print(msg)
    logging.info(msg)
   
# =========================
# 🧹 LIMPAR PASTA
# =========================

def limpar_pasta():
    os.makedirs(DOWNLOAD_PATH, exist_ok=True)

    for f in os.listdir(DOWNLOAD_PATH):
        try:
            os.remove(os.path.join(DOWNLOAD_PATH, f))
        except:
            pass

# =========================
# 🌐 DRIVER
# =========================

def iniciar_driver():
    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    prefs = {
        "download.default_directory": DOWNLOAD_PATH,
        "download.prompt_for_download": False
    }

    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=options)
    return driver

# =========================
# ⏳ DOWNLOAD
# =========================

def esperar_download(timeout=180):
    inicio = time.time()

    while True:
        arquivos = os.listdir(DOWNLOAD_PATH)

        if any(f.endswith(".crdownload") for f in arquivos):
            if time.time() - inicio > timeout:
                raise Exception("Timeout download")
            time.sleep(2)
            continue

        arquivos_validos = [f for f in arquivos if not f.endswith(".crdownload")]

        if arquivos_validos:
            return

        if time.time() - inicio > timeout:
            raise Exception("Nenhum arquivo baixado")

        time.sleep(2)

# =========================
# 🔐 LOGIN + DOWNLOAD
# =========================

def baixar_planilha():
    driver = iniciar_driver()
    wait = WebDriverWait(driver, 30)

    try:
        log("Acessando portal...")
        driver.get("https://web.wrsat.com.br/")

        usuario = wait.until(EC.element_to_be_clickable((By.ID, "usuario")))
        senha = wait.until(EC.element_to_be_clickable((By.ID, "senha")))

        usuario.send_keys(LOGIN)
        senha.send_keys(SENHA)

        driver.execute_script("""
            document.getElementById('login_btn').click();
        """)

        wait.until(EC.presence_of_element_located(
            (By.XPATH, "//span[contains(text(),'Página inicial')]")
        ))

        driver.find_element(By.ID, "download_excel").click()

        esperar_download()

    finally:
        driver.quit()

# =========================
# 📁 ARQUIVO
# =========================

def obter_arquivo_recente():
    arquivos = [
        os.path.join(DOWNLOAD_PATH, f)
        for f in os.listdir(DOWNLOAD_PATH)
    ]

    return max(arquivos, key=os.path.getctime)

# =========================
# 📡 N8N
# =========================

def enviar_para_n8n(caminho):
    with open(caminho, 'rb') as f:
        files = {'file': f}
        requests.post(N8N_WEBHOOK_URL, files=files)

# =========================
# 🔄 EXECUÇÃO
# =========================

def executar_automacao():
    for i in range(3):
        try:
            limpar_pasta()
            baixar_planilha()
            arquivo = obter_arquivo_recente()
            enviar_para_n8n(arquivo)
            log("Sucesso!")
            break
        except Exception as e:
            log(f"Erro tentativa {i+1}: {e}")
            time.sleep(5)

if __name__ == "__main__":
    executar_automacao()