import request from '@/utils/request'

export type LessonPlanStatus = 'queued' | 'generating' | 'completed' | 'failed'

export interface CourseSection {
  id: string
  name: string
  type: string
  path: string
  parent_id: string | null
  description: string
}

export interface LessonPlanCreatePayload {
  class_id: number
  course_id: number
  section_id: string
  include_review: boolean
  slide_count: number
}

export interface LessonPlanSlide {
  layout: string
  title: string
  bullets: string[]
  presenter_notes: string
  source_refs: string[]
}

export interface LessonPlanDraft {
  title: string
  summary: string
  review_inserted: boolean
  slides: LessonPlanSlide[]
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
