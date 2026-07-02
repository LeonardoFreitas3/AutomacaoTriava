# Triava Meeting Reminders

Esta é uma automação para a Triava que verifica o Google Calendar da conta `triava.business@gmail.com` diariamente e envia um e-mail de lembrete com a apresentação em anexo caso seja a primeira reunião com um novo contacto no dia seguinte.

## Como funciona
1. Um script em Python corre todos os dias no GitHub Actions.
2. Lê os eventos de amanhã.
3. Para cada participante (excepto o dono do calendário), verifica se já houve reuniões passadas com esse mesmo e-mail.
4. Se for a primeira vez que se vai reunir com o e-mail, envia a mensagem padrão com o link do evento, juntamente com o anexo `apresentacao_triava.pdf`.

## Configuração Inicial

Para que o script funcione no GitHub Actions sem intervenção humana, precisa de configurar a API do Google Workspace / Google Cloud:

1. **Criar um Projecto na Google Cloud**:
   - Vá a [Google Cloud Console](https://console.cloud.google.com/).
   - Crie um novo projecto.
   - Active a **Google Calendar API** e a **Gmail API**.

2. **Configurar as Credenciais**:
   - No menu lateral, vá a "APIs & Services" -> "Credentials".
   - Crie um **OAuth client ID** para uma **Desktop app**.
   - Faça download do ficheiro JSON e grave-o no seu computador como `credentials.json` na mesma pasta do código.
   - *(Atenção: não faça commit do credentials.json para o repositório público!)*

3. **Gerar o `token.json` Localmente**:
   - Na sua máquina local, instale as dependências: `pip install -r requirements.txt`.
   - Execute o script pela primeira vez: `python send_reminders.py`.
   - O seu browser vai abrir para fazer login na sua conta `triava.business@gmail.com` e autorizar o acesso ao Gmail e Calendar.
   - Após autorizar, será gerado um ficheiro `token.json`.

4. **Configurar os Secrets no GitHub**:
   - No seu repositório GitHub, vá a **Settings** -> **Secrets and variables** -> **Actions**.
   - Crie um secret chamado `GOOGLE_CREDENTIALS_JSON`. Copie o conteúdo inteiro do seu `credentials.json` e cole-o aqui.
   - Crie um secret chamado `GOOGLE_TOKEN_JSON`. Copie o conteúdo inteiro do seu `token.json` e cole-o aqui.

A partir daqui, a automação correrá sozinha.

## Substituir o Anexo
Actualmente existe um ficheiro `apresentacao_triava.pdf` que é um placeholder (apenas para teste). Substitua este ficheiro pela verdadeira apresentação da Triava mantendo o mesmo nome de ficheiro (`apresentacao_triava.pdf`), faça commit e push para o GitHub.

## Notas
- A automação está configurada para correr todos os dias às 18:00 UTC (ajuste na linha `cron:` no ficheiro `.github/workflows/daily_reminder.yml` se quiser noutra hora).
- Pode também correr o workflow manualmente no separador "Actions" do GitHub clicando em "Run workflow".
