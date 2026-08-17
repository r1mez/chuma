import request from '@/utils/request'

export type LessonPlanStatus = 'queued' | 'generating' | 'completed' | 'failed'
export type ThemePack = `theme${'01' | '02' | '03' | '04' | '05' | '06' | '07' | '08' | '09' | '10' | '11' | '12'}`

export interface CourseSection {
  id: string
  name: string
  type: string
  path: string
  parent_id: string | null
  description: string
}

export interface LessonPlanBlock {
  type: string
  title?: string
  text?: string
  items?: string[]
  steps?: string[]
  question?: string
  options?: string[]
  teacher_answer?: string
  left_title?: string
  left_items?: string[]
  right_title?: string
  right_items?: string[]
  language?: string
  code?: string
  columns?: string[]
  rows?: string[][]
  caption?: string
}

export interface LessonPlanCreatePayload {
  class_id: number
  course_id: number
  section_id: string
  include_review: boolean
  slide_count: number
  theme_pack: ThemePack
}

export interface LessonPlanSlide {
  layout: string
  title: string
  takeaway?: string
  bullets: string[]
  blocks?: LessonPlanBlock[]
  presenter_notes: string
  source_refs: string[]
  diagram_center?: string
  diagram_nodes?: string[]
  duration_minutes?: number
  narrative_job?: string
  learning_objective?: string
  student_prompt?: string
  expected_answer?: string
  visual_type?: string
  visual_description?: string
  source_evidence?: string[]
}

export interface LessonPlanDraft {
  title: string
  summary: string
  review_inserted: boolean
  slides: LessonPlanSlide[]
  quality_report?: {
    passed: boolean
    reports: Array<{
      phase: string
      passed: boolean
      issues: Array<{ code: string; message: string; slide_number?: number | null }>
      metrics: Record<string, unknown>
    }>
  }
}

export interface LessonPlanItem {
  lesson_plan_id: number
  title: string
  class_id: number
  class_name: string | null
  course_id: number
  course_name: string | null
  section_id: string
  section_name: string
  section_path: string
  previous_section_name: string | null
  include_review: boolean
  slide_count: number
  theme_pack: ThemePack
  task_id: string
  status: LessonPlanStatus
  content: LessonPlanDraft | null
  file_name: string | null
  error_message: string | null
  created_at: string
  updated_at: string
}

export function getCourseSections(courseId: number) {
  return request.get<CourseSection[]>(`/teacher/courses/${courseId}/sections`)
}

export function createLessonPlan(payload: LessonPlanCreatePayload) {
  return request.post<LessonPlanItem>('/teacher/lesson-plans', payload, { timeout: 45000 })
}

export function getLessonPlans() {
  return request.get<LessonPlanItem[]>('/teacher/lesson-plans')
}

export function getLessonPlan(lessonPlanId: number) {
  return request.get<LessonPlanItem>(`/teacher/lesson-plans/${lessonPlanId}`)
}

export function downloadLessonPlan(lessonPlanId: number) {
  return request.get<Blob>(`/teacher/lesson-plans/${lessonPlanId}/download`, { responseType: 'blob', timeout: 90000 })
}

export function getLessonPlanPreviewTicket(lessonPlanId: number) {
  return request.get<{ url: string }>(`/teacher/lesson-plans/${lessonPlanId}/preview-ticket`)
}
