@-- ============================================================
-- 智教慧学 — 学生侧数据模型建表脚本
-- 数据库: chuma (PostgreSQL)
-- 日期: 2026-07-20
-- 说明: 从零创建所有表（适用于全新数据库）
--       如果 kg_graphs 表已存在，请跳过第一段
-- ============================================================

-- 1. kg_graphs — 知识图谱元数据（如果已存在则跳过）
CREATE TABLE IF NOT EXISTS kg_graphs (
    id              BIGINT        PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    graph_name      VARCHAR(128)  NOT NULL UNIQUE,
    original_filename VARCHAR(256) NOT NULL,
    file_path       VARCHAR(512),
    node_count      INTEGER       DEFAULT 0,
    edge_count      INTEGER       DEFAULT 0,
    chunk_count     INTEGER       DEFAULT 0,
    status          VARCHAR(20)   DEFAULT 'pending',
    created_at      TIMESTAMP     DEFAULT now(),
    updated_at      TIMESTAMP     DEFAULT now()
);

-- 如果 kg_graphs 已存在且有 user_id 列，执行以下语句删除：
-- DROP INDEX IF EXISTS ix_kg_graphs_user_id;
-- ALTER TABLE kg_graphs DROP COLUMN IF EXISTS user_id;

-- 2. students — 学生表
CREATE TABLE students (
    stu_id          BIGINT        PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    stu_name        VARCHAR(64)   NOT NULL,
    stu_gender      VARCHAR(4),
    stu_email       VARCHAR(128)  UNIQUE,
    stu_pwd         VARCHAR(256),
    created_at      TIMESTAMP     DEFAULT now(),
    updated_at      TIMESTAMP     DEFAULT now()
);

-- 3. teachers — 教师表（预留）
CREATE TABLE teachers (
    tea_id          BIGINT        PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    tea_name        VARCHAR(64)   NOT NULL,
    tea_email       VARCHAR(128)  UNIQUE,
    tea_pwd         VARCHAR(256),
    created_at      TIMESTAMP     DEFAULT now(),
    updated_at      TIMESTAMP     DEFAULT now()
);

-- 4. courses — 学科表
CREATE TABLE courses (
    course_id           BIGINT        PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    course_name         VARCHAR(64)   NOT NULL UNIQUE,
    course_description  TEXT,
    kg_id               BIGINT        UNIQUE REFERENCES kg_graphs(id),
    created_at          TIMESTAMP     DEFAULT now(),
    updated_at          TIMESTAMP     DEFAULT now()
);

-- 5. questions — 题库表
CREATE TABLE questions (
    question_id         BIGINT        PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    question_description TEXT         NOT NULL,
    question_answer      TEXT         NOT NULL,
    question_options     JSON,
    question_type        VARCHAR(32)  NOT NULL,
    question_difficulty  SMALLINT     NOT NULL,
    question_explanation TEXT,
    course_id            BIGINT       NOT NULL REFERENCES courses(course_id),
    kg_node_name         VARCHAR(128),
    created_at           TIMESTAMP    DEFAULT now(),
    updated_at           TIMESTAMP    DEFAULT now(),
    CONSTRAINT ck_question_difficulty_range CHECK (question_difficulty >= 1 AND question_difficulty <= 5)
);
CREATE INDEX ix_questions_course_id    ON questions(course_id);
CREATE INDEX ix_questions_kg_node_name ON questions(kg_node_name);
CREATE INDEX ix_questions_difficulty   ON questions(question_difficulty);

-- 6. exercise_records — 做题记录表
CREATE TABLE exercise_records (
    do_id           BIGINT        PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    question_id     BIGINT        NOT NULL REFERENCES questions(question_id),
    stu_id          BIGINT        NOT NULL REFERENCES students(stu_id),
    kg_node_name    VARCHAR(128),
    do_stu_answer   TEXT          NOT NULL,
    do_score        FLOAT,
    created_at      TIMESTAMP     DEFAULT now(),
    CONSTRAINT ck_do_score_range CHECK (do_score >= 0.0 AND do_score <= 10.0)
);
CREATE INDEX ix_exercise_records_question_id   ON exercise_records(question_id);
CREATE INDEX ix_exercise_records_stu_id        ON exercise_records(stu_id);
CREATE INDEX ix_exercise_records_kg_node_name  ON exercise_records(kg_node_name);
CREATE INDEX ix_exercise_records_stu_node      ON exercise_records(stu_id, kg_node_name);

-- 7. student_course_mastery — 学生-学科掌握度表
CREATE TABLE student_course_mastery (
    stu_id          BIGINT    NOT NULL REFERENCES students(stu_id),
    course_id       BIGINT    NOT NULL REFERENCES courses(course_id),
    course_degree   FLOAT     NOT NULL,
    updated_at      TIMESTAMP DEFAULT now(),
    PRIMARY KEY (stu_id, course_id),
    CONSTRAINT ck_course_degree_range CHECK (course_degree >= 0.0 AND course_degree <= 5.0)
);

-- 8. student_knowledge_mastery — 学生-知识点掌握度表
CREATE TABLE student_knowledge_mastery (
    stu_id          BIGINT       NOT NULL REFERENCES students(stu_id),
    kg_node_name    VARCHAR(128) NOT NULL,
    kg_degree       FLOAT        NOT NULL,
    updated_at      TIMESTAMP    DEFAULT now(),
    PRIMARY KEY (stu_id, kg_node_name),
    CONSTRAINT ck_kg_degree_range CHECK (kg_degree >= 0.0 AND kg_degree <= 5.0)
);
CREATE INDEX ix_student_knowledge_mastery_node_name ON student_knowledge_mastery(kg_node_name);
