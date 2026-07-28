import request from '@/utils/request'

export interface Course {
  course_id: number;
  course_name: string;
  course_description?: string;
  kg_id?: number;
  created_at: string;
  updated_at: string;
}

export interface Question {
  question_id: number;
  question_description: string;
  question_answer: string;
  question_options?: any;
  question_type: string;
  question_difficulty: number;
  question_explanation?: string;
  course_id: number;
  kg_node_name?: string;
  created_at: string;
  updated_at: string;
}

// practice API 调用封装
export const fetchCourses = (): Promise<Course[]> => {
  return request.get<Course[]>('/practice/courses')
}

export const fetchQuestions = (courseId?: number, kgNodeName?: string, difficulty?: number): Promise<Question[]> => {
  return request.get<Question[]>('/practice/questions', {
    params: { course_id: courseId, kg_node_name: kgNodeName, difficulty }
  })
}

export const fetchQuestionById = (questionId: number): Promise<Question> => {
  return request.get<Question>(`/practice/questions/${questionId}`)
}

