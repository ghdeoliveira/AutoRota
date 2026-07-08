from flask import Flask, render_template, jsonify, request
from playwright.sync_api import sync_playwright
import requests
import re
import json
import logging
from datetime import datetime
import time
import os

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
        self.cookies_headers = None
    
    def add_log(self, message, tipo='info'):
        log_entry = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'message': message,
            'type': tipo
        }
        self.logs.append(log_entry)
        print(f"[{tipo.upper()}] {message}")
    
    def capturar_cookies_playwright(self):
        """Captura cookies e headers usando Playwright (rápido)"""
        self.add_log("🔍 Capturando autenticação...", 'info')
        
        try:
            with sync_playwright() as p:
                # Lança navegador headless (mais rápido que Selenium)
                browser = p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = context.new_page()
                
                # Acessa o formulário
                start_time = time.time()
                page.goto(self.view_url, wait_until='domcontentloaded')
                
                # Aguarda o radiogroup carregar (máximo 5 segundos)
                try:
                    page.wait_for_selector('div[role="radiogroup"]', timeout=5000)
                except:
                    self.add_log("⚠️ Tempo limite ao carregar formulário, mas continuando...", 'warning')
                
                elapsed = time.time() - start_time
                self.add_log(f"⏱️  Formulário carregado em {elapsed:.2f}s", 'info')
                
                # 1. Captura todos os cookies
                cookies = context.cookies()
                cookies_dict = {}
                for cookie in cookies:
                    cookies_dict[cookie['name']] = cookie['value']
                
                # 2. Captura o fbzx
                html = page.content()
                fbzx_match = re.search(r'fbzx" value="([^"]+)"', html)
                if fbzx_match:
                    cookies_dict['fbzx'] = fbzx_match.group(1)
                    self.add_log(f"🔑 fbzx: {cookies_dict['fbzx'][:20]}...", 'info')
                
                # 3. Captura o token (se existir)
                token_match = re.search(r'token" value="([^"]+)"', html)
                if token_match:
                    cookies_dict['token'] = token_match.group(1)
                    self.add_log(f"🔑 token: {cookies_dict['token'][:20]}...", 'info')
                
                # 4. Captura as rotas disponíveis (já aproveita)
                rotas = []
                opcoes = page.query_selector_all('div[role="radio"]')
                for opcao in opcoes:
                    data_value = opcao.get_attribute('data-value')
                    if data_value and data_value != '.' and data_value not in rotas:
                        rotas.append(data_value)
                
                # 5. Prepara headers de autenticação
                self.cookies_headers = {
                    'cookies': cookies_dict,
                    'rotas': rotas,
                    'html': html
                }
                
                browser.close()
                
                self.add_log(f"✅ {len(cookies_dict)} cookies e {len(rotas)} rotas capturadas!", 'success')
                return True
                
        except Exception as e:
            self.add_log(f"❌ Erro ao capturar cookies: {e}", 'error')
            return False
    
    def buscar_rotas_disponiveis(self):
        """Retorna as rotas já capturadas (sem nova requisição)"""
        if self.cookies_headers and 'rotas' in self.cookies_headers:
            rotas = self.cookies_headers['rotas']
            if rotas:
                self.add_log(f"📋 {len(rotas)} rotas disponíveis", 'info')
                for i, rota in enumerate(rotas, 1):
                    self.add_log(f"  {i}. {rota}", 'info')
                return rotas
        
        # Fallback: tenta capturar novamente
        if self.capturar_cookies_playwright():
            return self.cookies_headers.get('rotas', [])
        
        return []
    
    def selecionar_melhor_rota(self, rotas):
        if not rotas:
            return None
        
        self.add_log("🔍 Selecionando melhor rota...", 'info')
        
        # Filtra bloqueadas
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
        
        # Tenta prioridades
        for palavra in self.palavras_prioritarias:
            for rota in rotas_liberadas:
                if palavra.lower() in rota.lower():
                    self.add_log(f"🎯 ESCOLHIDA: {rota} (contém: {palavra})", 'success')
                    return rota
        
        rota = rotas_liberadas[0]
        self.add_log(f"⚠️ Usando primeira disponível: {rota}", 'warning')
        return rota
    
    def enviar_formulario(self, rota):
        """Envia o formulário usando requests (ultrarrápido)"""
        
        if not self.cookies_headers:
            self.add_log("⚠️ Capturando autenticação...", 'warning')
            if not self.capturar_cookies_playwright():
                return False
        
        cookies = self.cookies_headers.get('cookies', {})
        
        # Adiciona cookies à sessão
        for nome, valor in cookies.items():
            self.session.cookies.set(nome, valor)
        
        # Monta payload
        payload = {
            self.ENTRY_EMAIL: self.email,
            self.ENTRY_DRIVER_ID: self.driver_id,
            self.ENTRY_TELEFONE: self.telefone,
            self.ENTRY_ROTA: rota,
            'fvv': '1',
            'pageHistory': '0'
        }
        
        # Adiciona fbzx se tiver
        if 'fbzx' in cookies:
            payload['fbzx'] = cookies['fbzx']
        
        if 'token' in cookies:
            payload['token'] = cookies['token']
        
        # Headers
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
        
        self.add_log(f"📤 Enviando formulário...", 'info')
        
        start_time = time.time()
        
        try:
            response = self.session.post(
                self.submit_url,
                data=payload,
                headers=headers,
                allow_redirects=False,
                timeout=10
            )
            
            elapsed = time.time() - start_time
            status = response.status_code
            
            self.add_log(f"⏱️  Envio completado em {elapsed:.2f}s", 'info')
            self.add_log(f"📊 Status HTTP: {status}", 'info')
            
            if status in [200, 301, 302]:
                self.add_log(f"✅ FORMULÁRIO ENVIADO COM SUCESSO!", 'success')
                self.add_log(f"📍 Rota: {rota}", 'success')
                return True
            else:
                self.add_log(f"❌ Falha no envio. Status: {status}", 'error')
                if status == 401:
                    self.add_log("🔄 Tentando renovar autenticação...", 'warning')
                    self.cookies_headers = None
                    if self.capturar_cookies_playwright():
                        return self.enviar_formulario(rota)
                return False
                
        except Exception as e:
            self.add_log(f"❌ Erro no envio: {e}", 'error')
            return False
    
    def executar(self):
        """Executa o bot completo (otimizado para velocidade)"""
        self.logs = []
        tempo_total = time.time()
        
        self.add_log("━" * 40, 'info')
        self.add_log("🚀 Brilhante 2 Bot (Modo Rápido)", 'info')
        self.add_log("━" * 40, 'info')
        self.add_log(f"📧 Email: {self.email}", 'info')
        self.add_log(f"🆔 Driver ID: {self.driver_id}", 'info')
        self.add_log(f"📱 Telefone: {self.telefone}", 'info')
        self.add_log("━" * 40, 'info')
        
        # Passo 1: Capturar autenticação e rotas (uma única vez)
        if not self.cookies_headers:
            if not self.capturar_cookies_playwright():
                return {'sucesso': False, 'logs': self.logs}
        
        # Passo 2: Buscar rotas (já estão na memória)
        rotas = self.cookies_headers.get('rotas', [])
        if not rotas:
            self.add_log("❌ Nenhuma rota disponível!", 'error')
            return {'sucesso': False, 'logs': self.logs}
        
        # Passo 3: Selecionar melhor rota
        rota_escolhida = self.selecionar_melhor_rota(rotas)
        
        if not rota_escolhida:
            self.add_log("❌ Nenhuma rota atende aos critérios!", 'error')
            return {'sucesso': False, 'logs': self.logs}
        
        # Passo 4: Enviar formulário (requests - rápido)
        if self.enviar_formulario(rota_escolhida):
            self.add_log("━" * 40, 'info')
            self.add_log(f"🎉 PROCESSO FINALIZADO COM SUCESSO!", 'success')
            self.add_log(f"📍 Rota: {rota_escolhida}", 'success')
            self.add_log(f"⏱️  Tempo total: {time.time() - tempo_total:.2f}s", 'info')
            self.add_log("━" * 40, 'info')
            return {'sucesso': True, 'rota': rota_escolhida, 'logs': self.logs}
        else:
            self.add_log("━" * 40, 'info')
            self.add_log(f"❌ PROCESSO FINALIZADO COM FALHA!", 'error')
            self.add_log("━" * 40, 'info')
            return {'sucesso': False, 'logs': self.logs}


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
    print("🚀 Brilhante 2 Bot - Modo Rápido")
    print("📍 Acesse: http://localhost:5000")
    print("⏱️  Playwright (captura) + Requests (envio)")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)