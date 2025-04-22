@startuml
!define BPMN https://raw.githubusercontent.com/plantuml-stdlib/plantuml-stdlib/master/bpmn-1.0/

!include BPMN/BPMN.puml
!include BPMN/BPMNArtifacts.puml
!include BPMN/BPMNActivity.puml
!include BPMN/BPMNEvent.puml
!include BPMN/BPMNGateway.puml
!include BPMN/BPMNDataObject.puml

title IT Support Ticket Management Process - To-Be (Implemented Automated System)

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
participant "Automated System" as System
participant "IT Technician" as Tech
participant "Department Manager" as Manager

lane "End User" {
  StartEvent_1(start, "Issue\nIdentified") #green
  Activity_1(create_ticket, "Submit Ticket via\nWeb Portal", "User Task")
  Activity_2(provide_info, "Respond to\nAuto-Generated\nQueries", "User Task")
  Activity_3(confirm_resolution, "Verify Issue\nResolution", "User Task")
  Activity_4(rate_satisfaction, "Rate Solution\nQuality", "User Task")
  EndEvent_1(end, "Issue\nResolved") #red
}

lane "Automated System" {
  Activity_5(ai_analysis, "AI Analysis of\nTicket Content", "Service Task")
  Activity_6(auto_categorize, "Auto-Categorize\nTicket", "Service Task")
  Activity_7(sentiment_analysis, "Perform Sentiment\nAnalysis", "Service Task")
  Activity_8(auto_prioritize, "AI-Based\nPrioritization", "Service Task")
  Activity_9(smart_assign, "Smart Technician\nAssignment", "Service Task")
  Activity_10(auto_monitor, "Automated SLA\nTracking", "Service Task")
  Activity_11(auto_escalate, "Automated\nEscalation", "Service Task")
  Activity_12(auto_knowledge, "Knowledge Base\nSuggestion", "Service Task")
  Activity_13(auto_close, "Auto-Close\nTicket", "Service Task")
  Activity_14(ml_feedback, "ML Feedback\nLoop", "Service Task")
  Activity_15(auto_document, "Auto-Document\nResolution", "Service Task")
  Activity_16(auto_translate, "Translate Content\nIf Needed", "Service Task")
}

lane "IT Support" {
  Activity_17(review_ai, "Review AI\nSuggestions", "User Task")
  Activity_18(investigate, "Investigate with\nAI Assistance", "User Task")
  Activity_19(validate_kb, "Validate Knowledge\nBase Matches", "User Task")
  Activity_20(implement, "Implement\nSolution", "User Task")
  Activity_21(document, "Document with\nAI Templates", "User Task")
  Activity_22(approve_resolution, "Approve Final\nResolution", "User Task")
}

lane "Management" {
  Activity_23(review_dashboard, "Monitor Real-time\nDashboard", "User Task")
  Activity_24(handle_escalation, "Handle Auto-\nEscalated Issues", "User Task")
  Activity_25(analyze_trends, "Analyze Ticket\nTrends", "User Task")
}

Gateway_1(ai_confidence, "AI Confidence\nLevel?", "Exclusive Gateway")
Gateway_2(need_info, "Additional\nInfo Needed?", "Exclusive Gateway")
Gateway_3(is_resolved, "Issue\nResolved?", "Exclusive Gateway")
Gateway_4(user_satisfied, "User\nSatisfied?", "Exclusive Gateway")
Gateway_5(sla_breach, "SLA\nBreach Risk?", "Exclusive Gateway")
Gateway_6(auto_resolvable, "Auto-\nResolvable?", "Exclusive Gateway")

DataObject_1(sentiment_data, "Sentiment\nAnalysis")
DataObject_2(category_data, "Category\nPrediction")
DataObject_3(priority_data, "Priority\nSuggestion")
DataObject_4(history_data, "Historical\nTicket Data")
DataObject_5(staff_skills, "Staff Skills\nMatrix")
DataObject_6(knowledge_data, "Knowledge Base\nArticles")
DataObject_7(ml_models, "ML Training\nModels")

start --> create_ticket
create_ticket --> auto_translate
auto_translate --> ai_analysis

ai_analysis --> auto_categorize
ai_analysis ..> sentiment_data
auto_categorize ..> category_data

auto_categorize --> sentiment_analysis
sentiment_analysis --> auto_prioritize
auto_prioritize ..> sentiment_data
auto_prioritize ..> priority_data
auto_prioritize --> smart_assign
smart_assign ..> history_data
smart_assign ..> staff_skills

smart_assign --> auto_resolvable
auto_resolvable -- "Yes" --> auto_knowledge
auto_knowledge ..> knowledge_data
auto_knowledge --> auto_document
auto_document --> auto_close
auto_close --> rate_satisfaction
rate_satisfaction --> ml_feedback
ml_feedback ..> ml_models
ml_feedback --> end

auto_resolvable -- "No" --> ai_confidence
ai_confidence -- "High (>85%)" --> auto_monitor
ai_confidence -- "Low (<85%)" --> review_ai
review_ai --> auto_monitor

auto_monitor --> sla_breach
sla_breach -- "Yes" --> auto_escalate
auto_escalate --> handle_escalation
handle_escalation --> investigate

sla_breach -- "No" --> investigate
investigate ..> knowledge_data
investigate --> validate_kb
validate_kb --> need_info

need_info -- "Yes" --> auto_knowledge
auto_knowledge --> provide_info
provide_info --> investigate

need_info -- "No" --> implement
implement --> document
document --> approve_resolution
approve_resolution --> is_resolved

is_resolved -- "No" --> investigate
is_resolved -- "Yes" --> confirm_resolution
confirm_resolution --> user_satisfied

user_satisfied -- "No" --> investigate
user_satisfied -- "Yes" --> auto_close
auto_close --> ml_feedback
ml_feedback --> end

review_dashboard --> analyze_trends
analyze_trends ..> ml_models

note right of ai_analysis: Implemented using Google Cloud NLP - 97% processing efficiency
note right of auto_categorize: 87% accurate categorization with continuous learning
note right of smart_assign: Uses expertise match, workload balance, and SLA urgency scoring
note right of auto_monitor: Real-time SLA tracking with predictive breach detection
note right of auto_knowledge: Suggests top 3 most relevant knowledge base articles
note right of ml_feedback: System improves with each resolution - 3.5% monthly accuracy increase
note right of auto_translate: Supports 30+ languages through Google Cloud Translation
note right of sentiment_analysis: Detects urgency and user frustration for priority adjustment
@enduml
