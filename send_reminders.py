import os
import json
import base64
import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.message import EmailMessage
import mimetypes

SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]
MY_EMAIL = "triava.business@gmail.com"

def get_credentials():
    creds = None
    # Use token from environment if running in GitHub Actions
    if 'GOOGLE_TOKEN_JSON' in os.environ:
        token_info = json.loads(os.environ['GOOGLE_TOKEN_JSON'])
        creds = Credentials.from_authorized_user_info(token_info, SCOPES)
    elif os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if 'GOOGLE_CREDENTIALS_JSON' in os.environ:
                with open('credentials.json', 'w') as f:
                    f.write(os.environ['GOOGLE_CREDENTIALS_JSON'])
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return creds

def get_tomorrows_events(calendar_service):
    # Calculate start and end of tomorrow in UTC (or local, assuming UTC for simplicity)
    now = datetime.datetime.utcnow()
    tomorrow = now + datetime.timedelta(days=1)

    start_of_tomorrow = datetime.datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0).isoformat() + 'Z'
    end_of_tomorrow = datetime.datetime(tomorrow.year, tomorrow.month, tomorrow.day, 23, 59, 59).isoformat() + 'Z'

    events_result = calendar_service.events().list(
        calendarId='primary', timeMin=start_of_tomorrow, timeMax=end_of_tomorrow,
        singleEvents=True, orderBy='startTime').execute()
    return events_result.get('items', [])

def check_if_first_meeting(calendar_service, attendee_email, start_of_tomorrow, current_event_id):
    # Check if this email was an attendee in any past events before tomorrow
    events_result = calendar_service.events().list(
        calendarId='primary', q=attendee_email, timeMax=start_of_tomorrow,
        singleEvents=True).execute()

    past_events = events_result.get('items', [])

    # Base ID of current event, useful for recurring events where ID is `baseId_instanceDate`
    current_base_id = current_event_id.split('_')[0] if current_event_id else None

    print(f"  [DEBUG] Eventos encontrados na pesquisa para {attendee_email}: {len(past_events)}")

    for event in past_events:
        event_id = event.get('id', '')
        base_id = event_id.split('_')[0]
        event_summary = event.get('summary', 'Sem Título')
        event_date = event.get('start', {}).get('dateTime') or event.get('start', {}).get('date')

        print(f"    -> Analisando evento: '{event_summary}' a {event_date} (ID: {event_id})")

        # Ignore the exact event we are currently evaluating, including instances of the same recurring event
        if event_id == current_event_id or base_id == current_base_id:
            continue

        # Ignore cancelled events
        if event.get('status') == 'cancelled':
            continue

        attendees = event.get('attendees', [])
        for attendee in attendees:
            if attendee.get('email', '').lower() == attendee_email.lower():
                # Ignore if the attendee declined the past event
                if attendee.get('responseStatus') == 'declined':
                    continue

                # Found a past event with this attendee
                event_date = event.get('start', {}).get('dateTime') or event.get('start', {}).get('date')
                print(f"  -> Encontrada reunião anterior para {attendee_email}: '{event.get('summary')}' a {event_date} (ID: {event_id})")
                return False

    return True

def send_email(gmail_service, to_email, event_link):
    message = EmailMessage()

    content = f"""Olá!

Amanhã teremos a nossa primeira reunião — e estamos muito entusiasmados por finalmente podermos conversar consigo!

Da nossa parte, está tudo preparado para que seja um encontro produtivo e inspirador.

Agradecemos apenas que confirme a sua presença no invite e caso não tenha recebido pedimos que confirme no spam ou basta carregar neste link: {event_link}

(Podem também conhecer melhor o nosso trabalho em triava.pt ou consultar a apresentação em anexo.)

Até breve!"""

    message.set_content(content)
    message['To'] = to_email
    message['From'] = MY_EMAIL
    message['Subject'] = 'É amanhã a nossa primeira conversa!'

    # Attach the PDF
    attachment_path = 'apresentacao_triava.pdf'
    if os.path.exists(attachment_path):
        with open(attachment_path, 'rb') as f:
            pdf_data = f.read()
        message.add_attachment(
            pdf_data,
            maintype='application',
            subtype='pdf',
            filename=os.path.basename(attachment_path)
        )

    # Encode message
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    create_message = {'raw': encoded_message}

    try:
        if os.environ.get('DRY_RUN', 'false').lower() == 'true':
            print(f"DRY RUN: Would have sent email to {to_email}")
            return None

        send_message = (gmail_service.users().messages().send
                        (userId="me", body=create_message).execute())
        print(f"Email sent to {to_email} - Message Id: {send_message['id']}")
        return send_message
    except Exception as error:
        print(f"An error occurred sending email to {to_email}: {error}")
        return None

def main():
    # Allow running without actual credentials if DRY_RUN=true and no token provided
    if os.environ.get('DRY_RUN', 'false').lower() == 'true' and 'GOOGLE_TOKEN_JSON' not in os.environ and not os.path.exists('token.json'):
        print("DRY RUN mode and no credentials found. Exiting gracefully without making API calls.")
        return

    creds = get_credentials()
    calendar_service = build('calendar', 'v3', credentials=creds)
    gmail_service = build('gmail', 'v1', credentials=creds)

    events = get_tomorrows_events(calendar_service)
    if not events:
        print('No upcoming events found for tomorrow.')
        return

    now = datetime.datetime.utcnow()
    tomorrow = now + datetime.timedelta(days=1)
    start_of_tomorrow = datetime.datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0).isoformat() + 'Z'

    for event in events:
        event_start = event.get('start', {}).get('dateTime') or event.get('start', {}).get('date')
        print(f"Processing event: {event.get('summary')} at {event_start}")
        event_id = event.get('id')
        event_link = event.get('htmlLink', 'https://calendar.google.com/')
        attendees = event.get('attendees', [])

        for attendee in attendees:
            email = attendee.get('email', '')
            if not email or email.lower() == MY_EMAIL:
                continue

            print(f"Checking attendee: {email}")

            # Check if this is the first meeting with this attendee
            is_first = check_if_first_meeting(calendar_service, email, start_of_tomorrow, event_id)

            if is_first:
                print(f"First meeting detected for {email}. Sending reminder.")
                send_email(gmail_service, email, event_link)
            else:
                print(f"Not the first meeting for {email}. Skipping.")

if __name__ == '__main__':
    main()
