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
    
    def add_log(self, message, tipo='info'):
        log_entry = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'message': message,
            'type': tipo
        }
        self.logs.append(log_entry)
        print(f"[{tipo.upper()}] {message}")
    
    def buscar_rotas_disponiveis(self):
        """Busca as rotas disponíveis no formulário"""
        try:
            # Headers para simular navegador
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = self.session.get(self.view_url, headers=headers, timeout=10)
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
                # Salva HTML para debug
                with open('debug_form.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                self.add_log("📁 HTML salvo em 'debug_form.html'", 'info')
            
            return rotas
            
        except Exception as e:
            self.add_log(f"❌ Erro ao buscar rotas: {e}", 'error')
            return []
    
    def selecionar_melhor_rota(self, rotas):
        if not rotas:
            return None
        
        self.add_log("🔍 Analisando rotas...", 'info')
        
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
        self.add_log(f"⚠️ Usando primeira: {rota}", 'warning')
        return rota
    
    def capturar_fbzx(self):
        """Captura o token fbzx da página"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = self.session.get(self.view_url, headers=headers, timeout=10)
            match = re.search(r'fbzx" value="([^"]+)"', response.text)
            return match.group(1) if match else None
        except Exception:
            return None
    
    def enviar_formulario(self, rota):
        """Envia o formulário usando requests"""
        
        # Captura fbzx
        fbzx = self.capturar_fbzx()
        
        payload = {
            self.ENTRY_EMAIL: self.email,
            self.ENTRY_DRIVER_ID: self.driver_id,
            self.ENTRY_TELEFONE: self.telefone,
            self.ENTRY_ROTA: rota,
            'fvv': '1',
            'pageHistory': '0'
        }
        
        if fbzx:
            payload['fbzx'] = fbzx
            self.add_log(f"🔑 fbzx: {fbzx[:20]}...", 'info')
        else:
            self.add_log("⚠️ fbzx não encontrado!", 'warning')
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://docs.google.com',
            'Referer': self.view_url,
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
                
                # Diagnóstico do erro 401
                if status == 401:
                    self.add_log("🔧 Diagnóstico do erro 401:", 'warning')
                    self.add_log("  - O formulário exige login", 'warning')
                    self.add_log("  - Você precisa estar logado no navegador", 'warning')
                    self.add_log("  - Tente abrir o formulário no navegador e depois execute o bot", 'warning')
                
                return False
                
        except Exception as e:
            self.add_log(f"❌ Erro no envio: {e}", 'error')
            return False
    
    def executar(self):
        """Executa o bot completo"""
        self.logs = []
        self.add_log("━" * 50, 'info')
        self.add_log("🚀 Brilhante 2 Bot (Requests)", 'info')
        self.add_log("━" * 50, 'info')
        self.add_log(f"📧 Email: {self.email}", 'info')
        self.add_log(f"🆔 Driver ID: {self.driver_id}", 'info')
        self.add_log(f"📱 Telefone: {self.telefone}", 'info')
        self.add_log("━" * 50, 'info')
        
        # Busca rotas
        rotas = self.buscar_rotas_disponiveis()
        
        if not rotas:
            self.add_log("❌ Nenhuma rota disponível!", 'error')
            return {'sucesso': False, 'logs': self.logs}
        
        # Seleciona rota
        rota_escolhida = self.selecionar_melhor_rota(rotas)
        
        if not rota_escolhida:
            self.add_log("❌ Nenhuma rota atende aos critérios!", 'error')
            return {'sucesso': False, 'logs': self.logs}
        
        # Envia
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

@app.route('/api/debug_html', methods=['GET'])
def debug_html():
    """Retorna o HTML salvo para análise"""
    try:
        with open('debug_form.html', 'r', encoding='utf-8') as f:
            html = f.read()
        return html[:5000]  # Primeiros 5000 caracteres
    except FileNotFoundError:
        return "Arquivo debug_form.html não encontrado. Execute o bot primeiro."
    except Exception as e:
        return f"Erro ao ler arquivo: {e}"
    
    
if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Brilhante 2 Bot - Servidor Rodando!")
    print("📍 Acesse: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)