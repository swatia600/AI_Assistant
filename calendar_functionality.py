import common
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import json
import datetime
import re
import os.path
from dateutil import parser as date_parser
import pytz  # Add this import for timezone handling

def setup_google_calendar_api():
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
            with open("token.json", "w") as token:
                token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

def parse_meeting_details(user_input):
    # Initializing combined input with the initial user input
    combined_input = user_input
    required_fields = ['title', 'date', 'time']
    first = True
    while True:
        # Prompt for Local LLM: We are infomring it to respond only in JSON format
        question = (
            f"Extract meeting details from the following user input and return them strictly as a JSON object, "
            f"Return the output in JSON format with 'title', 'date', 'time', 'participants', and 'agenda' fields. "
            f"if it's just an appointment not a meeting keep participants as empty and keep title as any info provided by user for appointment"
            f"Only return JSON, no extra text.\n\n. Follow these rules:\n\n"
            f"1. If only a time is given (e.g., '4 pm'), assume today if the time is in the future, otherwise set the date to tomorrow, format for time should be HH:MM (24-hour format), and date should be yyyy-mm-dd.\n"
            f"2. If only a day or ordinal (e.g., 'Friday' or '8th') is provided, assume the closest upcoming date in Future (don't give any past dates) format yyyy-mm-dd.\n"
            f"3. If any of the information is not given in the input like date, time , title, participants, agenda strictly don't set any default value keep it empty"
            f"4. Do not use 'null' or any default values.\n\n"
            f"5. Use user input to generate the response, dont use anything from the samples provided below, but format should be like this"
            f"Sample User input: 'Schedule a meeting on Friday at 10 am with alice@example.com, bob@example.com about project updates.'\n"
            f"Sample Response: {{'title': 'Meeting', 'date': '2024-11-03', 'time': '10:00', 'participants': ['alice@example.com', 'bob@example.com'], 'agenda': 'Project updates'}}\n\n"
            f"**Don't provide any explaination just return the formatted JSON**"
            f"User input: '{combined_input}'"
        )

        response = common.ask_local_llm(question)
        try:
            # Extracting the JSON from response and parsing it
            json_str_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_str_match:
                json_str = json_str_match.group(0)

                # Replacing actual newlines with escaped newlines for JSON parsing
                json_str = json_str.replace('\n', '\\n')
                meeting_details = json.loads(json_str)
        except (json.JSONDecodeError, AttributeError):
            print("Failed to parse meeting details. Please try again.")
            return None

        # Checking for missing required fields  
        if first :
            main_meeting_details = meeting_details
            first = False
        else:
            for f in main_meeting_details:
                if not main_meeting_details.get(f):
                    main_meeting_details[f] = meeting_details.get(f)

        missing_fields = [field for field in required_fields if not main_meeting_details.get(field)]
        if not missing_fields:
            # All required fields are present
            return main_meeting_details
        else:
            # Informing the user about missing fields
            missing_fields_str = ', '.join(missing_fields)
            print(f"The following information is missing: {missing_fields_str}.")
            additional_input = input("Please provide the missing information: ")
            # Combining the new input with previous inputs
            combined_input += " " + additional_input.strip()

def parse_relative_date(date_text):
    try:
        # Try parsing with dateutil's parser, which handles relative terms like "next Friday"
        return date_parser.parse(date_text, fuzzy=True).date().isoformat()
    except (ValueError, OverflowError):
        print("Unable to interpret the provided date. Please provide a valid date.")
        return None

def confirm_date(parsed_date):
    confirmation = input(f"The date detected is {parsed_date}. Is this correct? (yes/no): ").strip().lower()
    if confirmation == 'yes':
        return parsed_date
    else:
        return input("Please enter the correct date (YYYY-MM-DD): ")

def confirm_time(parsed_time):
    confirmation = input(f"The time detected is {parsed_time}. Is this correct? (yes/no): ").strip().lower()
    if confirmation == 'yes':
        return parsed_time
    else:
        return input("Please enter the correct time (HH-MM), 24 hr format: ")

def check_for_conflict(calendar_service, start_datetime, end_datetime):
    # Convert to UTC for API compatibility
    start_utc = start_datetime.astimezone(pytz.UTC).isoformat().replace('+00:00', 'Z')
    end_utc = end_datetime.astimezone(pytz.UTC).isoformat().replace('+00:00', 'Z')

    # Use the Google Calendar API to check for conflicts
    events_result = calendar_service.events().list(
        calendarId='primary',
        timeMin=start_utc,
        timeMax=end_utc,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    return events_result.get('items', [])


def suggest_alternate_slots(calendar_service, start_datetime, duration=1, num_slots=3):
    available_slots = []
    for i in range(1, num_slots + 1):  # Suggest the specified number of alternate slots
        new_start = start_datetime + datetime.timedelta(hours=i)
        new_end = new_start + datetime.timedelta(hours=duration)
        if not check_for_conflict(calendar_service, new_start, new_end):
            available_slots.append(new_start)
    return available_slots

def schedule_meeting(user_input):
    calendar_service = setup_google_calendar_api()
    meeting_details = parse_meeting_details(user_input)
    
    if not meeting_details:
        print("Unable to schedule the meeting due to missing details.")
        return
    participant_emails = list()
    if meeting_details.get('participants'):
        for participant in meeting_details.get('participants'):
            participant_emails.append(common.find_recipient_email_with_llm(participant))
            
    try:
        # Parse date and time with explicit timezone
        meeting_details['date'] = confirm_date(meeting_details['date'])
        meeting_details['time'] = confirm_time(meeting_details['time'])
        tz = pytz.timezone('America/Chicago')
        start_datetime = tz.localize(datetime.datetime.strptime(f"{meeting_details['date']} {meeting_details['time']}", "%Y-%m-%d %H:%M"))
        end_datetime = start_datetime + datetime.timedelta(hours=1)  # Default meeting length 1 hour
    except ValueError:
        print("Invalid date or time format. Please try again.")
        return

    # Checking for conflicts
    conflicting_events = check_for_conflict(calendar_service, start_datetime, end_datetime)
    if conflicting_events:
        print("There is already an appointment at the requested time.")
        overwrite = input("Do you want still want to add this meeting along with the existing meeting? (yes/no): ").strip().lower()
        if overwrite != 'yes':
            available_slots = suggest_alternate_slots(calendar_service, start_datetime)
            if available_slots:
                print("\nSuggested available slots:")
                for idx, slot in enumerate(available_slots, 1):
                    print(f"{idx}. {slot.strftime('%Y-%m-%d %H:%M')} {tz}")
                
                # Prompt user to select a slot
                while True:
                    try:
                        slot_choice = int(input("Please choose a slot by entering the number (or 0 to cancel): "))
                        if slot_choice == 0:
                            print("Meeting scheduling canceled.")
                            return
                        elif 1 <= slot_choice <= len(available_slots):
                            selected_slot = available_slots[slot_choice - 1]
                            meeting_details['date'] = selected_slot.strftime('%Y-%m-%d')
                            meeting_details['time'] = selected_slot.strftime('%H:%M')
                            start_datetime = selected_slot
                            end_datetime = start_datetime + datetime.timedelta(hours=1)
                            break
                        else:
                            print("Invalid choice. Please enter a valid slot number.")
                    except ValueError:
                        print("Invalid input. Please enter a number.")
            else:
                print("No available slots found. Please choose another time manually.")
                return

    # Prepare the event data
    event = {
        'summary': meeting_details["title"],
        'description': meeting_details["agenda"],
        'start': {
            'dateTime': start_datetime.isoformat(),
            'timeZone': 'America/Chicago',
        },
        'end': {
            'dateTime': end_datetime.isoformat(),
            'timeZone': 'America/Chicago',
        },
        'attendees': [{'email': email.strip()} for email in participant_emails],
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 10},
            ],
        },
    }

    # Adding the event to Google Calendar
    try:
        event_result = calendar_service.events().insert(calendarId='primary', body=event).execute()
        print(f"Meeting scheduled successfully! Event link: {event_result.get('htmlLink')}")
    except Exception as e:
        print(f"An error occurred while scheduling the meeting: {e}")
