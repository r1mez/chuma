import request from '@/utils/request'

export interface TeacherCourse {
  course_id: number
  course_name: string
}

export interface CourseChapter {
  id: string
  name: string
}

export interface TeacherClass {
  class_id: number
  class_name: string
  classmates_num: number | null
  student_count: number
}

export interface ClassStudent {
  stu_id: number
  stu_name: string
  stu_level: string | null
  course_process: number | null
}

export interface DifficultKnowledgePoint {
  name: string
  count: number
  ratio: number
}

export interface DifficultChapter {
  name: string
  count: number
  ratio: number
}

export function getTeacherCourses() {
  return request.get<TeacherCourse[]>('/teacher/courses')
}

export function getCourseChapters(courseId: number) {
  return request.get<CourseChapter[]>(`/teacher/courses/${courseId}/chapters`)
}

export function getTeacherClasses() {
  return request.get<TeacherClass[]>('/teacher/classes')
}

export function getClassStudents(classId: number, courseId: number) {
  return request.get<ClassStudent[]>(`/teacher/classes/${classId}/students`, {
    params: { course_id: courseId },
  })
}

export function getDifficultKnowledge(classId: number, courseId: number) {
  return request.get<DifficultKnowledgePoint[]>(
    `/teacher/classes/${classId}/difficult-knowledge`,
    {
      params: { course_id: courseId },
    },
  )
}

export function getDifficultChapters(classId: number, courseId: number) {
  return request.get<DifficultChapter[]>(
    `/teacher/classes/${classId}/difficult-chapters`,
    {
      params: { course_id: courseId },
    },
  )
}
