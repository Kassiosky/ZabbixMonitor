# Zabbix Windows Tray Monitor

Este projeto é um aplicativo Windows Tray que utiliza a API do Zabbix para monitorar incidentes em tempo real. Ele exibe notificações e permite a visualização de gráficos diretamente da interface do Zabbix.

## 🚀 Funcionalidades
- Monitoramento contínuo de incidentes do Zabbix.
- Notificações na área de trabalho para novos incidentes.
- Interface gráfica via Tkinter para exibição dos problemas.
- Ícone na bandeja do sistema para acesso rápido.
- Autenticação na API do Zabbix e na interface web.
- Exibição de gráficos relacionados aos problemas detectados.

## 📋 Requisitos
- Python 3.8+
- Zabbix com API habilitada
- Um arquivo `.env` com as credenciais do Zabbix

## 🛠 Instalação
1. Clone este repositório:
   ```bash
   git clone https://github.com/seuusuario/zabbix-tray-monitor.git
   cd zabbix-tray-monitor
   ```
2. Crie um ambiente virtual (opcional, mas recomendado):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Crie um arquivo `.env` na pasta `includes/` com as seguintes variáveis:
   ```ini
   zabbix_url=https://seuzabbix.com
   zabbix_user=seu_usuario
   zabbix_password=sua_senha
   zabbix_token=seu_token
   ```

## ▶️ Uso
Para executar o aplicativo, basta rodar o script principal:
```bash
python main.py
```
O aplicativo será minimizado para a bandeja do sistema, monitorando incidentes e exibindo notificações conforme necessário.

## 🔧 Construção do Executável
Caso queira gerar um executável, utilize o PyInstaller:
```bash
pyinstaller --onefile --windowed --icon=icon.ico main.py
```
Isso criará um executável para rodar sem precisar do Python instalado.

## 📜 Licença
Este projeto está sob a licença MIT. Sinta-se livre para modificar e distribuir.

## 🤝 Contribuição
Se quiser contribuir, faça um fork do repositório, crie uma branch e envie um pull request!

---
**Desenvolvido por [~ Kassio Andrade~ ]**

