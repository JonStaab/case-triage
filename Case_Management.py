 # Display menu

import datetime
import json
from fastapi import FastAPI, HTTPException
import os
import tempfile
from pathlib import Path
from threading import RLock
from typing import Literal
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI, OpenAIError
from pydantic import BaseModel, Field, ConfigDict

BASE_DIR = Path(__file__).resolve().parent
CASES_FILE = Path(os.environ.get("CASES_FILE", str(BASE_DIR / "cases.json")))
case_lock = RLock()
app = FastAPI(title="Case Triage")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

@app.get("/", include_in_schema=False)
def web_app():
    return FileResponse(BASE_DIR / "static" / "index.html")

@app.get("/health")
def health():
    return {"status": "ok"}



def get_valid_choice(prompt, minimum, maximum):
    while True:
        try:
            choice = int(input(prompt))
        except ValueError:
            print("Please use a number.")
            continue

        if choice < minimum or choice > maximum:
            print(f"Please choose a number between {minimum} and {maximum}.")
            continue

        return choice

def case_to_dict(case):
    return {
        "unique_id": case.unique_id,
        "customer_name": case.customer_name,
        "issue_description": case.issue_description,
        "customer_tier": case.customer_tier,
        "business_impact": case.business_impact,
        "time_sensitivity": case.time_sensitivity,
        "priority": case.priority
    }


def save_cases(cases):
    case_data = []

    for case in cases:
        case_data.append(case_to_dict(case))



    CASES_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=CASES_FILE.parent,
                                         delete=False) as file:
            temporary = file.name
            json.dump(case_data, file, indent=4)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, CASES_FILE)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def load_cases():
    try:
        with CASES_FILE.open("r", encoding="utf-8") as file:
             case_data = json.load(file)
    except FileNotFoundError:
        return []

    cases = []
    for saved_case in case_data:
        new_case = Case(
            saved_case["unique_id"],
            saved_case["customer_name"],
            saved_case["issue_description"],
            saved_case["customer_tier"],
            saved_case["business_impact"],
            saved_case["time_sensitivity"],
            saved_case["priority"],
    )
        cases.append(new_case)

    return cases

def calculate_priority(time_sensitivity, business_impact, customer_tier):


    if customer_tier == "Low":
        tier = 1
    elif customer_tier == "Medium":
        tier = 2
    elif customer_tier == "High":
        tier = 3


    if business_impact == "Low":
        b_impact = 1
    elif business_impact == "Medium":
        b_impact = 2
    elif business_impact == "High":
        b_impact = 3
    elif business_impact == "Critical":
        b_impact = 4

    if time_sensitivity == "Low":
        t_impact = 1
    elif time_sensitivity == "Medium":
        t_impact = 2
    elif time_sensitivity == "High":
        t_impact = 3
    elif time_sensitivity == "Urgent":
        t_impact = 4
    elif time_sensitivity == "Critical":
        t_impact = 5

    total = t_impact + b_impact + tier

    if total >= 3 and total <= 4:
        priority = "P4"
    elif total >= 5 and total <= 7:
        priority = "P3"
    elif total >= 8 and total <=10:
        priority = "P2"
    elif total >= 11 and total <=12:
        priority = "P1"
    if b_impact == 4 and t_impact == 5:
        priority = "P1"

    return priority

class CaseCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    customer_name: str = Field(min_length=1, max_length=200)
    issue_description: str = Field(min_length=1, max_length=10000)
    customer_tier: Literal["Low", "Medium", "High"]
    business_impact: Literal["Low", "Medium", "High", "Critical"]
    time_sensitivity: Literal["Low", "Medium", "High", "Urgent", "Critical"]


class Case:
    def __init__(self, unique_id, customer_name, issue_description, customer_tier, business_impact, time_sensitivity, priority):
        self.unique_id = unique_id
        self.customer_name = customer_name
        self.issue_description = issue_description
        self.customer_tier = customer_tier
        self.business_impact = business_impact
        self.time_sensitivity = time_sensitivity
        self.priority = priority

def create_case(customer_name, issue_description, customer_tier,
                business_impact, time_sensitivity, cases):

    case_number = len(cases) + 1

    now = datetime.datetime.now()

    now = now.strftime("%m-%d-%Y-%H:%M-")

    priority = calculate_priority(time_sensitivity,business_impact, customer_tier)

    unique_id = f"{now}{case_number}"
    new_case = Case(unique_id, customer_name, issue_description, customer_tier, business_impact, time_sensitivity, priority)
    return new_case

cases = load_cases()

def summarize_case(issue_description):
    if not os.environ.get("OPENAI_API_KEY"):
        raise HTTPException(status_code=503, detail="AI summaries are unavailable. Set OPENAI_API_KEY on the server.")
    client = OpenAI(timeout=30.0, max_retries=1)
    response = client.responses.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-5.5"),
        input=f"Summarize this customer support issue in one concise sentence: {issue_description}"
    )
    return response.output_text
@app.get("/cases")
def get_cases():

    case_data = []


    for case in cases:
        case_data.append(case_to_dict(case))

    return case_data

@app.get("/cases/{case_id}")
def get_case(case_id: str):
    for case in cases:
        if case_id == case.unique_id:
            return case_to_dict(case)
    raise HTTPException(status_code=404, detail="Case not found")


@app.post("/cases")
def post_case(case_data: CaseCreate):
    with case_lock:
        new_case = create_case(
            case_data.customer_name, case_data.issue_description, case_data.customer_tier,
            case_data.business_impact, case_data.time_sensitivity, cases
        )
        try:
            save_cases(cases + [new_case])
        except OSError:
            raise HTTPException(status_code=503, detail="Case could not be saved. Please try again.")
        cases.append(new_case)
        return case_to_dict(new_case)

@app.post("/cases/{case_id}/summary")
def summarize_existing_case(case_id: str):
    for case in cases:
        if case.unique_id == case_id:
            try:
                summary = summarize_case(case.issue_description)
            except OpenAIError:
                raise HTTPException(status_code=502, detail="The AI service could not generate a summary. Please try again later.")
            return {
                "case_id": case.unique_id,
                "summary": summary
            }

    raise HTTPException(status_code=404, detail="Case not found")
#CASE MANAGEMENT SYSTEM

if __name__ == "__main__":
    while True:
        print("""
        1. Create Case
        2. View Cases
        3. Update Case
        4. Show Summary
        5. Exit
         """)


        # Get user's choice

        choice = get_valid_choice("What option do you choose: ",1,5)



        if choice == 1:


            customer_name = input(f"Customer Name: ")
            issue_description = input(f"Issue description: ")

            print("""
            1. - Low - Under $5m annual revenue 
            2. - Medium - $5m - $10m
            3. - High - Over $10m
            """)
            customer_tier_choice = get_valid_choice("Customer Tier: 1 - 3: ", 1, 3)

            if customer_tier_choice == 1:
                customer_tier = "Low"

            elif customer_tier_choice == 2:
                customer_tier = "Medium"

            elif customer_tier_choice == 3:
                customer_tier = "High"




            print(""" 
            1. Low - Minor inconvenience; work can continue
            2. Medium - Some functionality resricted
            3. High - Major workflow blocked
            4. Critical - Operations Stopped
            """)
            business_impact_choice = get_valid_choice("Business Impact: ",1,4)
            if business_impact_choice == 1:
                    business_impact = "Low"

            elif business_impact_choice == 2:
                    business_impact = "Medium"

            elif business_impact_choice == 3:
                    business_impact = "High"

            elif business_impact_choice == 4:
                business_impact = "Critical"


            print("""    
            1. Low - More than 2 weeks 
            2. Medium - 1 - 2 weeks
            3. High - within 1 week
            4. Urgent - By end of business day
            5. Critical - Immediate
            """)


            time_sensitivity_choice = get_valid_choice("Time Sensitivity Level: ",1,5)

            if time_sensitivity_choice == 1:
                time_sensitivity = "Low"

            elif time_sensitivity_choice == 2:
                time_sensitivity = "Medium"

            elif time_sensitivity_choice == 3:
                time_sensitivity = "High"

            elif time_sensitivity_choice == 4:
                time_sensitivity = "Urgent"

            elif time_sensitivity_choice == 5:
                time_sensitivity = "Critical"


            new_case = create_case(
                customer_name,
                issue_description,
                customer_tier,
                business_impact,
                time_sensitivity,
                cases
            )
            cases.append(new_case)
            save_cases(cases)
        elif choice == 2:
            for case in cases:
                print(f"Unique ID: {case.unique_id}"),
                print(f"Customer Name: {case.customer_name}"),
                print(f"Issue: {case.issue_description}"),
                print(f"Customer Tier: {case.customer_tier}"),
                print(f"Business Impact: {case.business_impact}"),
                print(f"Urgency: {case.time_sensitivity}"),
                print(f"Case Priority: {case.priority}"),
                print("-" * 40)


        elif choice == 3:
                case_id = input(f"Enter Case ID#: ")
                for case in cases:
                    if case_id == case.unique_id:
                        print(case.unique_id)

                        print("""
                        1. Customer Name
                        2. Issue Description 
                        3. Customer Tier
                        4. Business Impact
                        5. Time Sensitivity
                        """)
                        change_request = get_valid_choice("Choose which to update: ",1,5)
                        if change_request == 1:
                            new_customer_name = input("Enter new customer name: ")
                            case.customer_name = new_customer_name
                        elif change_request == 2:
                            new_issue_description = input("Enter new issue description: ")
                            case.issue_description = new_issue_description
                        elif change_request == 3:
                            print("""
                                    1. - Low - Under $5m annual revenue 
                                    2. - Medium - $5m - $10m
                                    3. - High - Over $10m
                                    """)
                            customer_tier_choice = get_valid_choice("Customer Tier: ",1,3)

                            if customer_tier_choice == 1:
                                customer_tier = "Low"

                            elif customer_tier_choice == 2:
                                customer_tier = "Medium"

                            elif customer_tier_choice == 3:
                                customer_tier = "High"

                            case.customer_tier = customer_tier
                        elif change_request == 4:
                            print("""    
                                   1. Low - Minor Inconvenience: work can continue 
                                   2. Medium - Some functionality restricted 
                                   3. High - Major workflow blocked
                                   4. Critical - Operations Stopped
                                   """)
                            business_impact_choice = get_valid_choice("Enter New Business Impact: ",1,4)

                            if business_impact_choice == 1:
                                business_impact = "Low"

                            elif business_impact_choice == 2:
                                business_impact = "Medium"

                            elif business_impact_choice == 3:
                                business_impact = "High"

                            elif business_impact_choice == 4:
                                business_impact = "Critical"


                            case.business_impact = business_impact
                            print("Case updated successfully.")
                        elif change_request == 5:
                            print("""    
                                    1. Low - More than 2 weeks 
                                    2. Medium - 1 - 2 weeks
                                    3. High - within 1 week
                                    4. Urgent - By end of business day
                                    5. Critical - Immediate
                                    """)
                            time_sensitivity_choice = get_valid_choice("Enter New Time Sensitivity: ",1,5)

                            if time_sensitivity_choice == 1:
                                time_sensitivity = "Low"

                            elif time_sensitivity_choice == 2:
                                time_sensitivity = "Medium"

                            elif time_sensitivity_choice == 3:
                                time_sensitivity = "High"

                            elif time_sensitivity_choice == 4:
                                time_sensitivity = "Urgent"

                            elif time_sensitivity_choice == 5:
                                time_sensitivity = "Critical"


                            case.time_sensitivity = time_sensitivity
                        case.priority = calculate_priority(
                            case.time_sensitivity, case.business_impact, case.customer_tier
                        )
                        save_cases(cases)
                        break
                else:
                    print("Case not found.")
        elif choice == 4:
            p1_count = 0
            p2_count = 0
            p3_count = 0
            p4_count = 0

            for case in cases:
                if case.priority == "P1":
                    p1_count += 1
                elif case.priority == "P2":
                    p2_count += 1
                elif case.priority == "P3":
                    p3_count += 1
                elif case.priority == "P4":
                    p4_count += 1

            total_cases = len(cases)

            print(f"Total Cases: {total_cases}")
            print(f"P1 Critical: {p1_count}")
            print(f"P2 High: {p2_count}")
            print(f"P3 Medium: {p3_count}")
            print(f"P4 Low: {p4_count}")



        if choice == 5:
            break


