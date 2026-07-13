from flask import Flask, render_template, jsonify
from playwright.sync_api import sync_playwright
import logging
from datetime import datetime
import time

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# 🔧 MIDDLEWARE CORS (resolve o problema)
# ═══════════════════════════════════════════════════════════
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

# ═══════════════════════════════════════════════════════════
# 🤖 BOT
# ═══════════════════════════════════════════════════════════
class Brilhante2Bot:
    def __init__(self):
        self.driver_id = '163347'
        self.telefone = '47996327935'
        self.email = 'gho8885@gmail.com'
        
        self.palavras_prioritarias = ['CEDROS', 'NOVA ESPERANÇA', 'MONTE ALEGRE', 'NAÇÕES']
        self.palavras_bloqueadas = ['BOTUVERÁ', 'GUABIRUBA', 'ITAJAÍ', 'BRILHANTE', 'ITAIPAVA', 'BRUSQUE', 'MOTO', 'FIORINO', 'CENTRO']
        
        self.form_url = 'https://docs.google.com/forms/d/e/1FAIpQLSdUHqCbEnEtmcJgcIiJ0D4RrucqoFfc1Ve-YhPIdUgY4sZnbQ/viewform'
        self.ultimo_log = []
    
    def add_log(self, mensagem, tipo='info'):
        entry = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'message': mensagem,
            'type': tipo
        }
        self.ultimo_log.append(entry)
        if len(self.ultimo_log) > 50:
            self.ultimo_log = self.ultimo_log[-50:]
        
        if tipo == 'error':
            logger.error(mensagem)
        elif tipo == 'success':
            logger.info(f"✅ {mensagem}")
        else:
            logger.info(mensagem)
    
    def selecionar_melhor_rota(self, rotas):
        if not rotas:
            return None
        
        liberadas = []
        for rota in rotas:
            bloqueada = False
            for palavra in self.palavras_bloqueadas:
                if palavra.upper() in rota.upper():
                    bloqueada = True
                    break
            if not bloqueada:
                liberadas.append(rota)
        
        if not liberadas:
            self.add_log("❌ Todas as rotas foram bloqueadas!", 'error')
            return None
        
        for palavra in self.palavras_prioritarias:
            for rota in liberadas:
                if palavra.upper() in rota.upper():
                    self.add_log(f"🎯 Rota escolhida: {rota} (contém: {palavra})", 'success')
                    return rota
        
        rota = liberadas[0]
        self.add_log(f"⚠️ Nenhuma prioridade encontrada. Usando: {rota}", 'warning')
        return rota
    
    def executar(self):
        self.ultimo_log = []
        self.add_log("━" * 40, 'info')
        self.add_log("🚀 INICIANDO BRILHANTE 2 BOT", 'info')
        self.add_log(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 'info')
        self.add_log("━" * 40, 'info')
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
                
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = context.new_page()
                
                self.add_log("🌐 Acessando formulário...", 'info')
                page.goto(self.form_url, wait_until='domcontentloaded', timeout=30000)
                
                try:
                    page.wait_for_selector('div[role="radiogroup"]', timeout=15000)
                    self.add_log("✅ Formulário carregado!", 'success')
                except:
                    self.add_log("⚠️ Timeout ao carregar, mas continuando...", 'warning')
                
                rotas = []
                opcoes = page.query_selector_all('div[role="radio"]')
                for opcao in opcoes:
                    data_value = opcao.get_attribute('data-value')
                    if data_value and data_value != '.' and data_value not in rotas:
                        rotas.append(data_value)
                
                self.add_log(f"📋 Rotas encontradas: {len(rotas)}", 'info')
                for i, rota in enumerate(rotas, 1):
                    self.add_log(f"  {i}. {rota}", 'info')
                
                if not rotas:
                    self.add_log("❌ Nenhuma rota disponível!", 'error')
                    browser.close()
                    return {'sucesso': False, 'logs': self.ultimo_log}
                
                rota_escolhida = self.selecionar_melhor_rota(rotas)
                if not rota_escolhida:
                    self.add_log("❌ Nenhuma rota atende aos critérios!", 'error')
                    browser.close()
                    return {'sucesso': False, 'logs': self.ultimo_log}
                
                self.add_log(f"🎯 Rota escolhida: {rota_escolhida}", 'success')
                
                self.add_log("📝 Preenchendo formulário...", 'info')
                
                try:
                    page.fill('input[aria-labelledby="i5"]', self.driver_id)
                    self.add_log(f"  ✅ Driver ID: {self.driver_id}", 'success')
                except:
                    page.fill('input[aria-label="Seu ID"]', self.driver_id)
                
                try:
                    page.fill('input[aria-labelledby="i10"]', self.telefone)
                    self.add_log(f"  ✅ Telefone: {self.telefone}", 'success')
                except:
                    page.fill('input[aria-label="Seu telefone"]', self.telefone)
                
                for opcao in page.query_selector_all('div[role="radio"]'):
                    data_value = opcao.get_attribute('data-value')
                    texto = opcao.text_content().strip()
                    if data_value == rota_escolhida or texto == rota_escolhida or rota_escolhida in texto:
                        opcao.click()
                        self.add_log(f"  ✅ Rota selecionada", 'success')
                        break
                
                self.add_log("📤 Enviando formulário...", 'info')
                page.click('span:has-text("Enviar")')
                time.sleep(3)
                
                if page.query_selector('text=Resposta enviada'):
                    self.add_log("✅ FORMULÁRIO ENVIADO COM SUCESSO!", 'success')
                else:
                    self.add_log("⚠️ Status desconhecido, mas continuando...", 'warning')
                
                browser.close()
                self.add_log("━" * 40, 'info')
                self.add_log(f"🎉 PROCESSO FINALIZADO COM SUCESSO!", 'success')
                self.add_log(f"📍 Rota: {rota_escolhida}", 'success')
                self.add_log("━" * 40, 'info')
                
                return {'sucesso': True, 'rota': rota_escolhida, 'logs': self.ultimo_log}
                
        except Exception as e:
            self.add_log(f"❌ ERRO: {str(e)}", 'error')
            return {'sucesso': False, 'logs': self.ultimo_log}


# ═══════════════════════════════════════════════════════════
# 🚀 FLASK - ROTAS
# ═══════════════════════════════════════════════════════════

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def status():
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'versao': 'Brilhante 2 Bot - Render'
    })

@app.route('/api/executar', methods=['GET', 'OPTIONS'])
def executar_bot():
    # Responde requisições OPTIONS (preflight) para CORS
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        bot = Brilhante2Bot()
        resultado = bot.executar()
        return jsonify(resultado)
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e),
            'logs': [{
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'message': f'❌ Erro: {str(e)}',
                'type': 'error'
            }]
        })


# ═══════════════════════════════════════════════════════════
# 🏃 EXECUÇÃO
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 BRILHANTE 2 BOT - RENDER")
    print("📍 Acesse: https://autorota.onrender.com")
    print("=" * 50)
    app.run(debug=False, host='0.0.0.0', port=5000)