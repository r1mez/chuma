import request from '@/utils/request'

// teacher API 调用封装

export interface TeacherCourse {
  course_id: number
  course_name: string
}

export interface TeacherClass {
  class_id: number
  class_name: string
  classmates_num: number | null
  student_count: number
}

// 获取当前登录教师所授学科列表
export function getTeacherCourses() {
  return request.get<TeacherCourse[]>('/teacher/courses')
}

// 获取当前登录教师所管班级列表（含学生数量）
export function getTeacherClasses() {
  return request.get<TeacherClass[]>('/teacher/classes')
}
