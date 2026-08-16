import request from '@/utils/request'

export interface AssignmentQuestion {
  question_id: number
  question_description: string
  question_options?: any
  question_type: string
  question_difficulty: number
  question_answer?: string
  question_explanation?: string
  course_id: number
  kg_node_name?: string
  sort_order: number
  priority_score?: number | null
  recommendation_source?: string | null
  recommendation_reason?: string | null
}

export interface AssignmentItem {
  assignment_id: number
  title: string
  description?: string | null
  class_id: number
  class_name?: string | null
  course_id: number
  course_name?: string | null
  due_at?: string | null
  status: string
  question_count: number
  submitted_count: number
  created_at: string
}

export interface StudentAssignment extends AssignmentItem {
  questions?: AssignmentQuestion[]
  submitted_question_ids?: number[]
  can_submit?: boolean
}

export interface AssignmentRecommendation extends AssignmentQuestion {
  attempted_students: number
  wrong_count: number
}

export interface AssignmentQuestionSelection {
  question_id: number
  sort_order?: number
  priority_score?: number | null
  recommendation_source?: string | null
  recommendation_reason?: string | null
}

export interface CreateAssignmentRequest {
  title: string
  description?: string
  class_id: number
  course_id: number
  due_at?: string | null
  questions: AssignmentQuestionSelection[]
}

export interface AssignmentResultStudent {
  stu_id: number
  stu_name: string
  submitted_count: number
  total_questions: number
  completion_rate: number
  average_score?: number | null
  accuracy?: number | null
  latest_submitted_at?: string | null
}

export interface AssignmentResults {
  assignment: AssignmentItem
  summary: {
    student_count: number
    submitted_student_count: number
    completed_student_count: number
    question_count: number
    completion_rate: number
    average_score: number | null
  }
  students: AssignmentResultStudent[]
}

export function fetchStudentAssignments() {
  return request.get<StudentAssignment[]>('/assignments')
}

export function fetchStudentAssignment(assignmentId: number) {
  return request.get<StudentAssignment>(`/assignments/${assignmentId}`)
}

export function fetchTeacherAssignments(classId?: number, courseId?: number) {
  return request.get<AssignmentItem[]>('/teacher/assignments', {
    params: { class_id: classId, course_id: courseId },
  })
}

export function fetchAssignmentRecommendations(classId: number, courseId: number, limit = 30) {
  return request.get<AssignmentRecommendation[]>('/teacher/assignment-recommendations', {
    params: { class_id: classId, course_id: courseId, limit },
  })
}

export function createAssignment(data: CreateAssignmentRequest) {
  return request.post<StudentAssignment>('/teacher/assignments', data)
}

export function fetchAssignmentResults(assignmentId: number) {
  return request.get<AssignmentResults>(`/teacher/assignments/${assignmentId}/results`)
}
