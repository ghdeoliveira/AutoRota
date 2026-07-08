from flask import Flask, render_template, jsonify, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
import requests
import re
import json
import logging
from datetime import datetime
import time
import os
import shutil

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

class GoogleFormsBotBrilhante2:
    def __init__(self, email, driver_id, telefone, palavras_prioritarias, palavras_bloqueadas):
        # ENTRIES DO FORMULÁRIO
        self.ENTRY_EMAIL = 'emailAddress'
        self.ENTRY_DRIVER_ID = 'entry.1941002046'
        self.ENTRY_TELEFONE = 'entry.1388004571'
        self.ENTRY_ROTA = 'entry.396510670'
        
        self.email = email
        self.driver_id = driver_id
        self.telefone = telefone
        self.palavras_prioritarias = palavras_prioritarias
        self.palavras_bloqueadas = palavras_bloqueadas
        
        self.form_id = '1FAIpQLSdUHqCbEnEtmcJgcIiJ0D4RrucqoFfc1Ve-YhPIdUgY4sZnbQ'
        self.view_url = f'https://docs.google.com/forms/d/e/{self.form_id}/viewform'
        self.submit_url = f'https://docs.google.com/forms/d/e/{self.form_id}/formResponse'
        
        self.session = requests.Session()
        self.logs = []
        self.driver = None
    
    def add_log(self, message, tipo='info'):
        log_entry = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'message': message,
            'type': tipo
        }
        self.logs.append(log_entry)
        print(f"[{tipo.upper()}] {message}")
    
    def encontrar_chromedriver(self):
        """Tenta encontrar o chromedriver em vários locais"""
        locais = [
            '/usr/local/bin/chromedriver',
            '/usr/bin/chromedriver',
            '/snap/bin/chromedriver',
            shutil.which('chromedriver')
        ]
        
        for local in locais:
            if local and os.path.exists(local):
                return local
        return None
    
    def configurar_driver(self):
        """Configura o ChromeDriver para capturar cookies"""
        options = Options()
        
        # MODO HEADLESS (sem janela)
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-setuid-sandbox')
        options.add_argument('--window-size=1280,800')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Carrega perfil do Chrome (mantém login)
        user_data_dir = os.path.expanduser('~/.config/google-chrome')
        if os.path.exists(user_data_dir):
            options.add_argument(f'--user-data-dir={user_data_dir}')
            options.add_argument('--profile-directory=Default')
            self.add_log("📁 Perfil Chrome carregado", 'info')
        
        chromedriver_path = self.encontrar_chromedriver()
        
        try:
            if chromedriver_path:
                service = Service(chromedriver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                self.driver = webdriver.Chrome(options=options)
            
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.add_log("✅ ChromeDriver configurado!", 'success')
            return True
        except Exception as e:
            self.add_log(f"❌ Erro: {e}", 'error')
            return False
    
    def capturar_cookies_autenticacao(self):
        """Captura os cookies de autenticação usando Selenium"""
        if not self.driver:
            return None
        
        try:
            self.add_log("🔍 Capturando cookies de autenticação...", 'info')
            
            # Acessa o formulário
            self.driver.get(self.view_url)
            
            # Aguarda carregar
            wait = WebDriverWait(self.driver, 30)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="radiogroup"]')))
            
            # Pega todos os cookies
            cookies = self.driver.get_cookies()
            
            # Filtra cookies importantes
            cookies_uteis = {}
            for cookie in cookies:
                nome = cookie['name']
                valor = cookie['value']
                cookies_uteis[nome] = valor
                self.add_log(f"🍪 Cookie: {nome}", 'info')
            
            # Adiciona cookies à sessão requests
            self.session.cookies.update(cookies_uteis)
            
            # Pega o fbzx da página
            html = self.driver.page_source
            fbzx_match = re.search(r'fbzx" value="([^"]+)"', html)
            if fbzx_match:
                fbzx = fbzx_match.group(1)
                self.session.cookies.set('fbzx', fbzx)
                self.add_log(f"🔑 fbzx: {fbzx[:20]}...", 'info')
            
            self.add_log(f"✅ {len(cookies_uteis)} cookies capturados!", 'success')
            
            return cookies_uteis
            
        except Exception as e:
            self.add_log(f"❌ Erro ao capturar cookies: {e}", 'error')
            return None
    
    def buscar_rotas_disponiveis(self):
        """Busca as rotas disponíveis no formulário"""
        try:
            # Primeiro, captura cookies se não tiver
            if not self.session.cookies:
                self.capturar_cookies_autenticacao()
            
            response = self.session.get(self.view_url, timeout=10)
            response.raise_for_status()
            html = response.text
            
            rotas = []
            
            # Busca via FB_PUBLIC_LOAD_DATA_
            fb_match = re.search(r'FB_PUBLIC_LOAD_DATA_\s*=\s*(\[.*?\]);', html, re.DOTALL)
            if fb_match:
                try:
                    data = json.loads(fb_match.group(1))
                    if data and len(data) > 1 and data[1]:
                        questions = data[1][1] if len(data[1]) > 1 else []
                        for question in questions:
                            if question and isinstance(question, list):
                                titulo = str(question[0]) if len(question) > 0 and question[0] else ""
                                if 'rota' in titulo.lower() or 'selecione' in titulo.lower():
                                    if len(question) > 4 and question[4]:
                                        for opt in question[4]:
                                            if opt and isinstance(opt, list) and len(opt) > 0:
                                                rota = opt[0] if opt[0] else (opt[1] if len(opt) > 1 else None)
                                                if rota and rota != '.' and rota not in rotas and len(str(rota)) > 2:
                                                    rotas.append(str(rota))
                except Exception as e:
                    pass
            
            rotas = list(dict.fromkeys(rotas))
            
            if rotas:
                self.add_log(f"✅ {len(rotas)} rotas encontradas!", 'success')
                for i, rota in enumerate(rotas, 1):
                    self.add_log(f"  {i}. {rota}", 'info')
            else:
                self.add_log("⚠️ Nenhuma rota encontrada!", 'warning')
            
            return rotas
            
        except Exception as e:
            self.add_log(f"❌ Erro ao buscar rotas: {e}", 'error')
            return []
    
    def selecionar_melhor_rota(self, rotas):
        if not rotas:
            return None
        
        self.add_log("🔍 Analisando rotas disponíveis...", 'info')
        
        rotas_liberadas = []
        for rota in rotas:
            bloqueada = False
            for palavra in self.palavras_bloqueadas:
                if palavra.lower() in rota.lower():
                    self.add_log(f"🚫 BLOQUEADA: {rota} (contém: {palavra})", 'warning')
                    bloqueada = True
                    break
            if not bloqueada:
                rotas_liberadas.append(rota)
                self.add_log(f"✅ LIBERADA: {rota}", 'success')
        
        if not rotas_liberadas:
            self.add_log("❌ Todas as rotas foram bloqueadas!", 'error')
            return None
        
        for palavra in self.palavras_prioritarias:
            for rota in rotas_liberadas:
                if palavra.lower() in rota.lower():
                    self.add_log(f"🎯 ESCOLHIDA: {rota} (contém: {palavra})", 'success')
                    return rota
        
        rota = rotas_liberadas[0]
        self.add_log(f"⚠️ Usando primeira disponível: {rota}", 'warning')
        return rota
    
    def enviar_formulario(self, rota):
        """Envia o formulário com a rota escolhida usando cookies autenticados"""
        
        # Verifica se tem cookies
        if not self.session.cookies:
            self.add_log("⚠️ Capturando cookies de autenticação...", 'warning')
            self.capturar_cookies_autenticacao()
        
        if not self.session.cookies:
            self.add_log("❌ Não foi possível capturar cookies!", 'error')
            return False
        
        # Monta o payload
        payload = {
            self.ENTRY_EMAIL: self.email,
            self.ENTRY_DRIVER_ID: self.driver_id,
            self.ENTRY_TELEFONE: self.telefone,
            self.ENTRY_ROTA: rota,
            'fvv': '1',
            'pageHistory': '0'
        }
        
        # Captura o fbzx da página
        try:
            response_get = self.session.get(self.view_url, timeout=10)
            html = response_get.text
            fbzx_match = re.search(r'fbzx" value="([^"]+)"', html)
            if fbzx_match:
                payload['fbzx'] = fbzx_match.group(1)
                self.add_log(f"🔑 fbzx: {payload['fbzx'][:20]}...", 'info')
        except Exception as e:
            self.add_log(f"⚠️ Erro ao capturar fbzx: {e}", 'warning')
        
        # Headers com autenticação
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://docs.google.com',
            'Referer': self.view_url,
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Upgrade-Insecure-Requests': '1',
        }
        
        self.add_log(f"📤 Enviando formulário com rota: {rota}", 'info')
        
        try:
            response = self.session.post(
                self.submit_url,
                data=payload,
                headers=headers,
                allow_redirects=False,
                timeout=30
            )
            
            status = response.status_code
            self.add_log(f"📊 Status HTTP: {status}", 'info')
            
            if status in [200, 301, 302]:
                self.add_log(f"✅ FORMULÁRIO ENVIADO COM SUCESSO!", 'success')
                self.add_log(f"📍 Rota: {rota}", 'success')
                return True
            else:
                self.add_log(f"❌ Falha no envio. Status: {status}", 'error')
                if status == 401:
                    self.add_log("🔧 Tentando renovar autenticação...", 'warning')
                    # Tenta renovar cookies
                    self.capturar_cookies_autenticacao()
                    # Tenta novamente (recursão simples)
                    return self.enviar_formulario(rota)
                return False
                
        except Exception as e:
            self.add_log(f"❌ Erro no envio: {e}", 'error')
            return False
    
    def executar(self):
        """Executa o bot completo"""
        self.logs = []
        self.add_log("━" * 50, 'info')
        self.add_log("🚀 Brilhante 2 Bot (Selenium + Requests)", 'info')
        self.add_log("━" * 50, 'info')
        self.add_log(f"📧 Email: {self.email}", 'info')
        self.add_log(f"🆔 Driver ID: {self.driver_id}", 'info')
        self.add_log(f"📱 Telefone: {self.telefone}", 'info')
        self.add_log("━" * 50, 'info')
        
        # Configura driver para capturar cookies
        if not self.configurar_driver():
            self.add_log("❌ Falha ao configurar driver!", 'error')
            return {'sucesso': False, 'logs': self.logs}
        
        try:
            # Busca rotas disponíveis
            rotas = self.buscar_rotas_disponiveis()
            
            if not rotas:
                self.add_log("❌ Nenhuma rota disponível no momento!", 'error')
                return {'sucesso': False, 'logs': self.logs}
            
            # Seleciona a melhor rota
            rota_escolhida = self.selecionar_melhor_rota(rotas)
            
            if not rota_escolhida:
                self.add_log("❌ Nenhuma rota atende aos critérios!", 'error')
                return {'sucesso': False, 'logs': self.logs}
            
            # Envia o formulário
            if self.enviar_formulario(rota_escolhida):
                self.add_log("━" * 50, 'info')
                self.add_log(f"🎉 PROCESSO FINALIZADO COM SUCESSO!", 'success')
                self.add_log(f"📍 Rota: {rota_escolhida}", 'success')
                self.add_log("━" * 50, 'info')
                return {'sucesso': True, 'rota': rota_escolhida, 'logs': self.logs}
            else:
                self.add_log("━" * 50, 'info')
                self.add_log(f"❌ PROCESSO FINALIZADO COM FALHA!", 'error')
                self.add_log("━" * 50, 'info')
                return {'sucesso': False, 'logs': self.logs}
                
        except Exception as e:
            self.add_log(f"❌ Erro inesperado: {e}", 'error')
            return {'sucesso': False, 'logs': self.logs}
        finally:
            if self.driver:
                self.driver.quit()
                self.add_log("🔄 Navegador fechado", 'info')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/enviar', methods=['POST'])
def enviar():
    data = request.json
    
    bot = GoogleFormsBotBrilhante2(
        email=data.get('email', 'gho8885@gmail.com'),
        driver_id=data.get('driverId', '163347'),
        telefone=data.get('telefone', '47996327935'),
        palavras_prioritarias = data.get('prioridades', ['CEDROS', 'NOVA ESPERANÇA', 'MONTE ALEGRE', 'NAÇÕES']),
        palavras_bloqueadas = data.get('bloqueadas', ['BOTUVERÁ', 'GUABIRUBA', 'ITAIPAVA', 'BRUSQUE', 'MOTO', 'FIORINO', 'CENTRO'])
    )
    
    resultado = bot.executar()
    return jsonify(resultado)


if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Brilhante 2 Bot - Servidor Rodando!")
    print("📍 Acesse: http://localhost:5000")
    print("📸 Modo: Selenium (headless) + Requests")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)