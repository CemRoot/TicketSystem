@startuml
!define BPMN https://raw.githubusercontent.com/plantuml-stdlib/plantuml-stdlib/master/bpmn-1.0/

!include BPMN/BPMN.puml
!include BPMN/BPMNArtifacts.puml
!include BPMN/BPMNActivity.puml
!include BPMN/BPMNEvent.puml
!include BPMN/BPMNGateway.puml
!include BPMN/BPMNDataObject.puml

title IT Support Ticket Management Process - As-Is (Current Manual Process)

!$BpmnElementColors = {
  "backgroundColor": "#FFFFFF",
  "borderColor": "#000000",
  "arrowColor": "#000000",
  "startEventColor": "#5cb85c",
  "endEventColor": "#d9534f",
  "activityColor": "#5bc0de",
  "gatewayColor": "#f0ad4e",
  "groupColor": "#999999"
}

participant "End User" as User
participant "Service Desk Agent" as Agent
participant "IT Technician" as Tech
participant "Department Manager" as Manager

lane "End User" {
  StartEvent_1(start, "Issue\nIdentified") #green
  Activity_1(create_ticket, "Create Support\nTicket Request", "User Task")
  Activity_2(provide_info, "Provide Additional\nInformation", "User Task")
  Activity_3(confirm_resolution, "Verify Issue\nResolution", "User Task")
  Activity_4(submit_feedback, "Submit Satisfaction\nFeedback", "User Task")
  EndEvent_1(end, "Issue\nResolved") #red
}

lane "Service Desk" {
  Activity_5(review_ticket, "Review Ticket\nRequest", "Manual Task")
  Activity_6(categorize, "Manually Categorize\nTicket", "Manual Task")
  Activity_7(prioritize, "Assign Priority\nLevel", "Manual Task")
  Activity_8(assign, "Assign to\nTechnician", "Manual Task")
  Activity_9(monitor, "Monitor SLA\nCompliance", "Manual Task")
  Activity_10(update_status, "Update Ticket\nStatus", "Manual Task")
  Activity_11(close_ticket, "Close\nTicket", "Manual Task")
  Activity_12(escalate, "Escalate to\nManager", "Manual Task")
}

lane "IT Support" {
  Activity_13(investigate, "Investigate\nIssue", "Manual Task")
  Activity_14(search_kb, "Search Knowledge\nBase Manually", "Manual Task")
  Activity_15(communicate, "Communicate with\nUser", "Manual Task")
  Activity_16(implement, "Implement\nSolution", "Manual Task")
  Activity_17(document, "Document\nResolution", "Manual Task")
  Activity_18(follow_up, "Follow-up with\nUser", "Manual Task")
}

lane "Management" {
  Activity_19(review_escalated, "Review Escalated\nTicket", "Manual Task")
  Activity_20(reassign, "Reassign\nTicket", "Manual Task")
  Activity_21(prioritize_resources, "Allocate Additional\nResources", "Manual Task")
}

Gateway_1(need_info, "Additional\nInfo Needed?", "Exclusive Gateway")
Gateway_2(is_resolved, "Issue\nResolved?", "Exclusive Gateway")
Gateway_3(user_satisfied, "User\nSatisfied?", "Exclusive Gateway")
Gateway_4(sla_at_risk, "SLA at\nRisk?", "Exclusive Gateway")
Gateway_5(complex_issue, "Complex\nIssue?", "Exclusive Gateway")

DataObject_1(ticket_info, "Ticket\nInformation")
DataObject_2(knowledge_base, "Knowledge\nBase")
DataObject_3(manual_notes, "Technician\nNotes")

start --> create_ticket
create_ticket --> review_ticket
create_ticket ..> ticket_info

review_ticket --> categorize
categorize --> prioritize
prioritize --> assign

assign --> investigate
investigate ..> ticket_info
investigate --> search_kb
search_kb ..> knowledge_base
search_kb --> complex_issue

complex_issue -- "Yes" --> escalate
escalate --> review_escalated
review_escalated --> reassign
reassign --> prioritize_resources
prioritize_resources --> investigate

complex_issue -- "No" --> need_info

need_info -- "Yes" --> communicate
communicate --> provide_info
provide_info --> investigate

need_info -- "No" --> implement
implement --> document
document ..> manual_notes
document --> is_resolved

is_resolved -- "No" --> investigate
is_resolved -- "Yes" --> update_status

monitor --> sla_at_risk
sla_at_risk -- "Yes" --> escalate
sla_at_risk -- "No" --> follow_up

update_status --> confirm_resolution
confirm_resolution --> user_satisfied
user_satisfied -- "No" --> investigate
user_satisfied -- "Yes" --> submit_feedback
submit_feedback --> close_ticket
close_ticket --> end

note right of categorize: 30% error rate in manual categorization
note right of assign: Assignment based solely on availability, not expertise match
note right of search_kb: Time-consuming manual searches with limited results
note right of monitor: Reactive SLA monitoring often misses critical breaches
note right of need_info: Communication delays average 4-6 hours
note right of complex_issue: 35% of tickets require escalation due to improper initial routing
@enduml
