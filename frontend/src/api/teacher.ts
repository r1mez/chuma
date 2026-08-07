import request from '@/utils/request'
import type { GraphData } from '@/api/knowledge'
import type { MasteryHierarchy } from '@/api/learning'

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

export interface StudentKnowledgeGraph {
  graph: GraphData
  mastery: MasteryHierarchy
}

/** 获取某学生在某学科下的个人知识图谱（图数据 + 掌握度层级树）。
 *  后端严格校验当前教师-班级-学科-学生对应关系，越权返回空对象。
 */
export function getStudentKnowledgeGraph(studentId: number, courseId: number) {
  return request.get<StudentKnowledgeGraph>(
    `/teacher/students/${studentId}/knowledge-graph`,
    {
      params: { course_id: courseId },
    },
  )
}
