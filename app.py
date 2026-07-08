from flask import Flask, render_template, jsonify, request
import requests
import re
import json
import logging
from datetime import datetime
import time

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

class GoogleFormsBotBrilhante2:
    def __init__(self, email, driver_id, telefone, palavras_prioritarias, palavras_bloqueadas):
        # ENTRIES DO FORMULÁRIO BRILHANTE 2
        self.ENTRY_EMAIL = 'entry.396510670'  # ← MUDANÇA: email agora é entry também!
        self.ENTRY_DRIVER_ID = 'entry.1941002046'
        self.ENTRY_TELEFONE = 'entry.1388004571'
        self.ENTRY_ROTA = 'entry.396510670'   # ← ATENÇÃO: mesmo entry do email? Verificar!
        
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
    
    def add_log(self, message, tipo='info'):
        log_entry = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'message': message,
            'type': tipo
        }
        self.logs.append(log_entry)
        print(f"[{tipo.upper()}] {message}")
    
    def capturar_dados_formulario(self):
        """Captura todos os dados necessários do formulário (tokens, entries, etc)"""
        try:
            response = self.session.get(self.view_url, timeout=10)
            response.raise_for_status()
            html = response.text
            
            dados = {
                'fbzx': None,
                'token': None,
                'entries': {},
                'rotas': []
            }
            
            # 1. Captura o fbzx
            fbzx_match = re.search(r'fbzx" value="([^"]+)"', html)
            if fbzx_match:
                dados['fbzx'] = fbzx_match.group(1)
                self.add_log(f"🔑 fbzx capturado: {dados['fbzx'][:20]}...", 'info')
            
            # 2. Captura o token (se existir)
            token_match = re.search(r'token" value="([^"]+)"', html)
            if token_match:
                dados['token'] = token_match.group(1)
                self.add_log(f"🔑 token capturado: {dados['token'][:20]}...", 'info')
            
            # 3. Busca no FB_PUBLIC_LOAD_DATA_ para descobrir os entries corretos
            fb_match = re.search(r'FB_PUBLIC_LOAD_DATA_\s*=\s*(\[.*?\]);', html, re.DOTALL)
            if fb_match:
                try:
                    data = json.loads(fb_match.group(1))
                    if data and len(data) > 1 and data[1]:
                        questions = data[1][1] if len(data[1]) > 1 else []
                        for question in questions:
                            if question and isinstance(question, list):
                                titulo = str(question[0]) if len(question) > 0 and question[0] else ""
                                
                                # Pega o entry ID (geralmente na posição 3)
                                entry_id = None
                                if len(question) > 3 and question[3]:
                                    if isinstance(question[3], list) and len(question[3]) > 0:
                                        entry_id = question[3][0]
                                    else:
                                        entry_id = question[3]
                                
                                if entry_id:
                                    dados['entries'][titulo] = entry_id
                                    self.add_log(f"📝 {titulo}: entry.{entry_id}", 'info')
                                    
                                    # Se for a pergunta das rotas, captura as opções
                                    if 'rota' in titulo.lower() or 'selecione' in titulo.lower():
                                        if len(question) > 4 and question[4]:
                                            for opt in question[4]:
                                                if opt and isinstance(opt, list) and len(opt) > 0:
                                                    rota = opt[0] if opt[0] else (opt[1] if len(opt) > 1 else None)
                                                    if rota and rota != '.' and rota not in dados['rotas']:
                                                        dados['rotas'].append(str(rota))
                except Exception as e:
                    self.add_log(f"⚠️ Erro ao parsear FB_DATA: {e}", 'warning')
            
            return dados
            
        except Exception as e:
            self.add_log(f"❌ Erro ao capturar dados: {e}", 'error')
            return None
    
    def buscar_rotas_disponiveis(self):
        """Busca as rotas disponíveis no formulário"""
        try:
            response = self.session.get(self.view_url, timeout=10)
            response.raise_for_status()
            html = response.text
            
            rotas = []
            
            # MÉTODO 1: Busca via FB_PUBLIC_LOAD_DATA_
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
            
            # MÉTODO 2: Fallback - busca por data-value
            if not rotas:
                radio_pattern = r'<div[^>]*data-value="([^"]*)"[^>]*role="radio"[^>]*>'
                matches = re.findall(radio_pattern, html)
                for value in matches:
                    if value and value != '.' and value not in rotas and len(value) > 2:
                        rotas.append(value)
            
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
    
    def pegar_fbzx(self):
        """Captura o token de segurança fbzx"""
        try:
            response = self.session.get(self.view_url, timeout=10)
            match = re.search(r'fbzx" value="([^"]+)"', response.text)
            return match.group(1) if match else None
        except Exception:
            return None
    
    def enviar_formulario(self, rota):
        """Envia o formulário com a rota escolhida - VERSÃO CORRIGIDA"""
        
        # 🔍 Primeiro, captura todos os dados do formulário
        dados_form = self.capturar_dados_formulario()
        if not dados_form:
            self.add_log("❌ Não foi possível capturar os dados do formulário!", 'error')
            return False
        
        # 🔧 Usa os entries corretos (se encontrados)
        entry_email = dados_form['entries'].get('E-mail', 'entry.396510670') if dados_form else 'entry.396510670'
        entry_driver = dados_form['entries'].get('ID Driver', 'entry.1941002046') if dados_form else 'entry.1941002046'
        entry_telefone = dados_form['entries'].get('Telefone de contato', 'entry.1388004571') if dados_form else 'entry.1388004571'
        entry_rota = dados_form['entries'].get('Selecione uma rota disponível', 'entry.396510670') if dados_form else 'entry.396510670'
        
        # ⚠️ IMPORTANTE: No formulário Brilhante 2, o E-mail usa o mesmo entry da Rota?
        # Vamos usar o entry correto baseado no que capturamos
        if entry_email == entry_rota:
            self.add_log("⚠️ E-mail e Rota têm o mesmo entry! Usando 'emailAddress' para o e-mail.", 'warning')
            entry_email = 'emailAddress'
        
        self.add_log(f"📝 Entries usados:", 'info')
        self.add_log(f"  E-mail: {entry_email}", 'info')
        self.add_log(f"  Driver ID: {entry_driver}", 'info')
        self.add_log(f"  Telefone: {entry_telefone}", 'info')
        self.add_log(f"  Rota: {entry_rota}", 'info')
        
        # Monta o payload
        payload = {
            entry_email: self.email,
            entry_driver: self.driver_id,
            entry_telefone: self.telefone,
            entry_rota: rota,
            'fvv': '1',
            'pageHistory': '0'
        }
        
        # Adiciona tokens de segurança
        fbzx = dados_form['fbzx'] if dados_form else self.pegar_fbzx()
        if fbzx:
            payload['fbzx'] = fbzx
            self.add_log(f"🔑 fbzx adicionado", 'info')
        
        token = dados_form['token'] if dados_form else None
        if token:
            payload['token'] = token
            self.add_log(f"🔑 token adicionado", 'info')
        
        # Headers completos (simulando um navegador real)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://docs.google.com',
            'Referer': self.view_url,
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
        
        # Mostra o payload (sem os valores sensíveis)
        payload_show = payload.copy()
        if 'fbzx' in payload_show:
            payload_show['fbzx'] = '***'
        if 'token' in payload_show:
            payload_show['token'] = '***'
        self.add_log(f"📤 Payload: {payload_show}", 'info')
        
        try:
            self.add_log(f"📤 Enviando formulário...", 'info')
            response = self.session.post(
                self.submit_url,
                data=payload,
                headers=headers,
                allow_redirects=False,
                timeout=30
            )
            
            status = response.status_code
            self.add_log(f"📊 Status HTTP: {status}", 'info')
            
            # Verifica o conteúdo da resposta para diagnóstico
            if response.text:
                response_preview = response.text[:500]
                self.add_log(f"📝 Resposta: {response_preview}", 'info')
            
            if status in [200, 301, 302]:
                self.add_log(f"✅ FORMULÁRIO ENVIADO COM SUCESSO!", 'success')
                self.add_log(f"📍 Rota: {rota}", 'success')
                return True
            else:
                self.add_log(f"❌ Falha no envio. Status: {status}", 'error')
                
                # Diagnóstico do erro 401
                if status == 401:
                    self.add_log("🔧 Diagnóstico do erro 401:", 'warning')
                    self.add_log("  - Verifique se o fbzx está correto", 'warning')
                    self.add_log("  - O formulário pode exigir login", 'warning')
                    self.add_log("  - Tente abrir o formulário no navegador para verificar", 'warning')
                    self.add_log("  - O token pode ter expirado", 'warning')
                
                return False
                
        except Exception as e:
            self.add_log(f"❌ Erro no envio: {e}", 'error')
            return False
    
    def executar(self):
        """Executa o bot completo"""
        self.logs = []
        self.add_log("━" * 50, 'info')
        self.add_log("🚀 Iniciando Brilhante 2 Bot", 'info')
        self.add_log("━" * 50, 'info')
        self.add_log(f"📧 Email: {self.email}", 'info')
        self.add_log(f"🆔 Driver ID: {self.driver_id}", 'info')
        self.add_log(f"📱 Telefone: {self.telefone}", 'info')
        self.add_log(f"🎯 Prioridades: {', '.join(self.palavras_prioritarias)}", 'info')
        self.add_log(f"🚫 Bloqueadas: {', '.join(self.palavras_bloqueadas)}", 'info')
        self.add_log("━" * 50, 'info')
        
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
            self.add_log("━" * 50, 'info')
            return {'sucesso': True, 'rota': rota_escolhida, 'logs': self.logs}
        else:
            self.add_log("━" * 50, 'info')
            self.add_log(f"❌ PROCESSO FINALIZADO COM FALHA!", 'error')
            self.add_log("━" * 50, 'info')
            return {'sucesso': False, 'logs': self.logs}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/enviar', methods=['POST'])
def enviar():
    data = request.json
    
    email = data.get('email', 'gho8885@gmail.com')
    driver_id = data.get('driverId', '163347')
    telefone = data.get('telefone', '47996327935')
    palavras_prioritarias = data.get('prioridades', ['CEDROS', 'NOVA ESPERANÇA', 'MONTE ALEGRE', 'NAÇÕES'])
    palavras_bloqueadas = data.get('bloqueadas', ['BOTUVERÁ', 'GUABIRUBA', 'ITAIPAVA', 'BRUSQUE', 'MOTO', 'FIORINO', 'CENTRO'])
    
    bot = GoogleFormsBotBrilhante2(
        email=email,
        driver_id=driver_id,
        telefone=telefone,
        palavras_prioritarias=palavras_prioritarias,
        palavras_bloqueadas=palavras_bloqueadas
    )
    
    resultado = bot.executar()
    return jsonify(resultado)


@app.route('/api/rotas', methods=['GET'])
def listar_rotas():
    """Endpoint para listar as rotas disponíveis sem enviar"""
    bot = GoogleFormsBotBrilhante2('', '', '', [], [])
    rotas = bot.buscar_rotas_disponiveis()
    return jsonify({'rotas': rotas})


@app.route('/api/debug', methods=['GET'])
def debug_formulario():
    """Endpoint para debug: mostra informações do formulário"""
    bot = GoogleFormsBotBrilhante2('', '', '', [], [])
    dados = bot.capturar_dados_formulario()
    return jsonify(dados)


if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Brilhante 2 Bot - Servidor Rodando!")
    print("📍 Acesse: http://localhost:5000")
    print("📍 Debug: http://localhost:5000/api/debug")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)