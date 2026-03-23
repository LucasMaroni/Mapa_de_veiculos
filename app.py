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
from webdriver_manager.chrome import ChromeDriverManager


# =========================
# 🔧 CONFIGURAÇÕES
# =========================

LOGIN = "Lucas.alves"
SENHA = "Lucxss180702@"

DOWNLOAD_PATH = r"C:\Downloads"

# 🔗 WEBHOOK N8N
N8N_WEBHOOK_URL = "https://n8n.srv1162985.hstgr.cloud/webhook-test/upload-planilha"


# =========================
# 📝 LOG
# =========================

logging.basicConfig(
    filename="automacao.log",
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
    if not os.path.exists(DOWNLOAD_PATH):
        os.makedirs(DOWNLOAD_PATH)

    for f in os.listdir(DOWNLOAD_PATH):
        caminho = os.path.join(DOWNLOAD_PATH, f)
        if os.path.isfile(caminho):
            try:
                os.remove(caminho)
            except:
                pass


# =========================
# 🌐 DRIVER
# =========================

def iniciar_driver():
    options = Options()

    # 🔥 Ativar quando for pra VM
    # options.add_argument("--headless=new")

    prefs = {
        "download.default_directory": DOWNLOAD_PATH,
        "download.prompt_for_download": False
    }

    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    driver.maximize_window()
    return driver


# =========================
# ⏳ ESPERAR DOWNLOAD
# =========================

def esperar_download(timeout=180):
    log("⏳ Aguardando download...")

    inicio = time.time()

    while True:
        arquivos = os.listdir(DOWNLOAD_PATH)

        if any(f.endswith(".crdownload") for f in arquivos):
            if time.time() - inicio > timeout:
                raise Exception("Timeout download")
            time.sleep(2)
            continue

        arquivos_validos = [
            f for f in arquivos if not f.endswith(".crdownload")
        ]

        if arquivos_validos:
            break

        if time.time() - inicio > timeout:
            raise Exception("Nenhum arquivo baixado")

        time.sleep(2)

    log("✅ Download concluído")


# =========================
# 🔐 LOGIN + DOWNLOAD
# =========================

def baixar_planilha():
    driver = iniciar_driver()
    wait = WebDriverWait(driver, 30)

    try:
        log("🌐 Acessando portal...")
        driver.get("https://web.wrsat.com.br/")

        usuario = wait.until(EC.element_to_be_clickable((By.ID, "usuario")))
        senha = wait.until(EC.element_to_be_clickable((By.ID, "senha")))

        log("🔐 Preenchendo login...")

        usuario.send_keys(LOGIN)
        senha.send_keys(SENHA)

        # Força botão login
        driver.execute_script("""
            let btn = document.getElementById('login_btn');
            btn.classList.remove('disabled');
            btn.disabled = false;
        """)

        time.sleep(1)
        driver.execute_script("document.getElementById('login_btn').click();")

        log("✅ Login realizado")

        # Página inicial
        wait.until(EC.presence_of_element_located(
            (By.XPATH, "//span[contains(text(),'Página inicial')]")
        ))

        log("📂 Indo para Página inicial...")
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//span[contains(text(),'Página inicial')]")
        )).click()

        # Botão download
        wait.until(EC.presence_of_element_located((By.ID, "download_excel")))

        log("⬇️ Clicando no download...")
        driver.find_element(By.ID, "download_excel").click()

        esperar_download()

    finally:
        try:
            driver.quit()
        except:
            pass


# =========================
# 📁 OBTER ARQUIVO
# =========================

def obter_arquivo_recente():
    arquivos = [
        os.path.join(DOWNLOAD_PATH, f)
        for f in os.listdir(DOWNLOAD_PATH)
        if os.path.isfile(os.path.join(DOWNLOAD_PATH, f))
    ]

    if not arquivos:
        raise Exception("Nenhum arquivo encontrado")

    arquivo = max(arquivos, key=os.path.getctime)

    log(f"📄 Arquivo encontrado: {arquivo}")
    return arquivo


# =========================
# 📡 ENVIAR PARA N8N
# =========================

def enviar_para_n8n(caminho_arquivo):
    log("📡 Enviando arquivo para n8n...")

    with open(caminho_arquivo, 'rb') as f:
        files = {
            'file': (
                os.path.basename(caminho_arquivo),
                f,
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        }

        response = requests.post(N8N_WEBHOOK_URL, files=files)

    if response.status_code in [200, 201]:
        log("✅ Enviado para n8n com sucesso!")
    else:
        raise Exception(f"Erro no envio: {response.text}")


# =========================
# 🔄 EXECUÇÃO
# =========================

def executar_automacao():
    for tentativa in range(3):
        try:
            log("🚀 INÍCIO DA AUTOMAÇÃO")

            limpar_pasta()
            baixar_planilha()
            arquivo = obter_arquivo_recente()
            enviar_para_n8n(arquivo)

            log("🏁 FINALIZADO COM SUCESSO")
            break

        except Exception as e:
            log(f"⚠️ Tentativa {tentativa + 1} falhou: {e}")
            time.sleep(5)


# =========================
# ▶️ MAIN
# =========================

if __name__ == "__main__":
    executar_automacao()