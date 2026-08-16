"""Built-in Agent registrations."""

from app.agent import tools as _builtin_tools  # noqa: F401 - load local tools
from app.agent.class_teaching_agent import ClassTeachingAgent
from app.agent.context import AgentContext
from app.agent.learning_plan_agent import LearningPlanAgent
from app.agent.lesson_plan_agent import LessonPlanAgent, execute_lesson_plan
from app.agent.orchestrator import AgentOrchestrator
from app.agent.qa_score_agent import QaScoreAgent
from app.agent.question_analysis_agent import QuestionAnalysisAgent
from app.agent.registry import AgentDefinition, AgentRegistry
from app.agent.stu_analysis_agent import StuAnalysisAgent
from app.agent.teacher_class_agent import TeacherClassAgent
from app.engines.llm.client import LLMClient


# The student tutor keeps the same tool contract as the previously working
# implementation. Other tools may be registered in this process, but are not
# exposed to this Agent.
STUDENT_TUTOR_TOOLS = frozenset(
    {
        "search_kg",
        "read_document",
        "query_my_mastery",
        "query_my_exercises",
        "socratic_hint",
    }
)


def _build_student_tutor(context: AgentContext, llm: LLMClient) -> AgentOrchestrator:
    return AgentOrchestrator(
        user_id=context.user_id,
        llm_client=llm,
        context=context,
    )


def _build_teacher_class_assistant(
    context: AgentContext,
    llm: LLMClient,
) -> TeacherClassAgent:
    return TeacherClassAgent(context=context, llm_client=llm)


def _build_class_teaching_suggestion(
    context: AgentContext,
    llm: LLMClient,
) -> ClassTeachingAgent:
    return ClassTeachingAgent(llm_client=llm)


def _build_teacher_lesson_plan(
    context: AgentContext,
    llm: LLMClient,
) -> LessonPlanAgent:
    return LessonPlanAgent(llm_client=llm)


def _build_student_analysis(context: AgentContext, llm: LLMClient) -> StuAnalysisAgent:
    return StuAnalysisAgent(llm_client=llm)


def _build_learning_plan(context: AgentContext, llm: LLMClient) -> LearningPlanAgent:
    return LearningPlanAgent(llm_client=llm)


def _build_question_analysis(
    context: AgentContext,
    llm: LLMClient,
) -> QuestionAnalysisAgent:
    return QuestionAnalysisAgent(llm_client=llm)


def _build_qa_score(context: AgentContext, llm: LLMClient) -> QaScoreAgent:
    return QaScoreAgent(llm_client=llm)


async def _execute_student_analysis(
    context: AgentContext,
    llm: LLMClient,
    payload: dict,
):
    return await _build_student_analysis(context, llm).analyze(
        context.student_id or context.user_id
    )


async def _execute_learning_plan(context: AgentContext, llm: LLMClient, payload: dict):
    return await _build_learning_plan(context, llm).generate(
        context.student_id or context.user_id
    )


async def _execute_question_analysis(
    context: AgentContext,
    llm: LLMClient,
    payload: dict,
):
    question_id = payload.get("question_id")
    if not isinstance(question_id, int):
        raise ValueError("question_id is required")
    return await _build_question_analysis(context, llm).analyze(
        question_id=question_id,
        do_stu_answer=payload.get("do_stu_answer"),
        stu_id=context.student_id,
    )


async def _execute_qa_score(context: AgentContext, llm: LLMClient, payload: dict):
    required = ("question_description", "question_answer", "stu_answer")
    if any(not isinstance(payload.get(key), str) for key in required):
        raise ValueError("question_description, question_answer and stu_answer are required")
    return await _build_qa_score(context, llm).score(
        payload["question_description"],
        payload["question_answer"],
        payload["stu_answer"],
    )


async def _execute_class_teaching_suggestion(
    context: AgentContext,
    llm: LLMClient,
    payload: dict,
):
    class_id = context.class_id or payload.get("class_id")
    course_id = context.course_id or payload.get("course_id")
    if not isinstance(class_id, int) or not isinstance(course_id, int):
        raise ValueError("class_id and course_id are required")
    course_name = payload.get("course_name")
    if course_name is not None and not isinstance(course_name, str):
        raise ValueError("course_name must be a string")
    return await _build_class_teaching_suggestion(context, llm).generate(
        class_id=class_id,
        course_id=course_id,
        course_name=course_name,
    )


async def _execute_teacher_lesson_plan(
    context: AgentContext,
    llm: LLMClient,
    payload: dict,
):
    return await execute_lesson_plan(context, llm, payload)


def register_builtin_agents() -> None:
    definitions = {
        "student.tutor": AgentDefinition(
            agent_id="student.tutor",
            display_name="Student Tutor",
            description="Student knowledge graph, document retrieval, and learning assistant",
            mode="chat",
            factory=_build_student_tutor,
            allowed_roles=frozenset({"student", "teacher", "admin", "service"}),
            allowed_tools=STUDENT_TUTOR_TOOLS,
        ),
        "teacher.class_assistant": AgentDefinition(
            agent_id="teacher.class_assistant",
            display_name="Teacher Class Assistant",
            description="Read-only class learning analytics assistant for teachers",
            mode="chat",
            factory=_build_teacher_class_assistant,
            allowed_roles=frozenset({"teacher"}),
        ),
        "student.analysis": AgentDefinition(
            agent_id="student.analysis",
            display_name="Student Learning Analysis",
            description="Structured analysis of a student's learning state",
            mode="workflow",
            factory=_build_student_analysis,
            executor=_execute_student_analysis,
            allowed_roles=frozenset({"student", "teacher", "admin", "service"}),
        ),
        "student.learning_plan": AgentDefinition(
            agent_id="student.learning_plan",
            display_name="Student Learning Plan",
            description="Generate subject-specific learning plans from multiple data dimensions",
            mode="workflow",
            factory=_build_learning_plan,
            executor=_execute_learning_plan,
            allowed_roles=frozenset({"student", "teacher", "admin", "service"}),
        ),
        "student.question_analysis": AgentDefinition(
            agent_id="student.question_analysis",
            display_name="Question Analysis",
            description="Analyze a question, a student's answer, and its knowledge graph context",
            mode="workflow",
            factory=_build_question_analysis,
            executor=_execute_question_analysis,
            allowed_roles=frozenset({"student", "teacher", "admin", "service"}),
        ),
        "student.qa_score": AgentDefinition(
            agent_id="student.qa_score",
            display_name="Short Answer Scoring",
            description="Score a student's short answer against the reference answer",
            mode="workflow",
            factory=_build_qa_score,
            executor=_execute_qa_score,
            allowed_roles=frozenset({"student", "teacher", "admin", "service"}),
        ),
        "teacher.class_teaching_suggestion": AgentDefinition(
            agent_id="teacher.class_teaching_suggestion",
            display_name="Class Teaching Suggestion",
            description="Generate a structured teaching suggestion from class learning analytics",
            mode="workflow",
            factory=_build_class_teaching_suggestion,
            executor=_execute_class_teaching_suggestion,
            allowed_roles=frozenset({"teacher", "admin", "service"}),
        ),
        "teacher.lesson_plan": AgentDefinition(
            agent_id="teacher.lesson_plan",
            display_name="Teacher Lesson Plan",
            description="Generate source-aware lesson-plan slide specifications for teachers",
            mode="workflow",
            factory=_build_teacher_lesson_plan,
            executor=_execute_teacher_lesson_plan,
            allowed_roles=frozenset({"teacher", "admin", "service"}),
        ),
    }

    registered = {item.agent_id for item in AgentRegistry.list()}
    for agent_id, definition in definitions.items():
        if agent_id not in registered:
            AgentRegistry.register(definition)


register_builtin_agents()
