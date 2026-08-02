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

export interface ClassStudent {
  stu_id: number
  stu_name: string
  stu_level: string | null
  course_process: number | null
}

// 获取当前登录教师所授学科列表
export function getTeacherCourses() {
  return request.get<TeacherCourse[]>('/teacher/courses')
}

// 获取当前登录教师所管班级列表（含学生数量）
export function getTeacherClasses() {
  return request.get<TeacherClass[]>('/teacher/classes')
}

// 获取指定班级的学生列表（含所选学科的学习进度与评级）
export function getClassStudents(classId: number, courseId: number) {
  return request.get<ClassStudent[]>('/teacher/classes/' + classId + '/students', {
    params: { course_id: courseId },
  })
}
