#!/usr/bin/env python3
"""Interactive Onboarding Wizard for AI Job Search Assistant.

Guides new users through:
1. Basic identity & search criteria (Name, City, Role, Work type, Location constraints, Compensation, Languages).
2. Generating a customized skills_checklist.md tailored to their target role.
3. Parsing checked skills (y/n or [x]) from skills_checklist.md and populating:
   - .claude/skills/job-application-assistant/01-candidate-profile.md
   - .claude/skills/job-application-assistant/02-behavioral-profile.md
   - .claude/skills/job-application-assistant/04-job-evaluation.md
   - .claude/skills/job-scraper/search-queries.md
   - cv/main_example.tex
"""

import os
import sys
import re
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROFILE_01 = ROOT / ".claude" / "skills" / "job-application-assistant" / "01-candidate-profile.md"
BEHAVIORAL_02 = ROOT / ".claude" / "skills" / "job-application-assistant" / "02-behavioral-profile.md"
EVALUATION_04 = ROOT / ".claude" / "skills" / "job-application-assistant" / "04-job-evaluation.md"
QUERIES_FILE = ROOT / ".claude" / "skills" / "job-scraper" / "search-queries.md"
CV_FILE = ROOT / "cv" / "main_example.tex"
CHECKLIST_FILE = ROOT / "skills_checklist.md"
CONFIGURED_MARKER = ROOT / ".setup_completed"

# Built-in skills knowledge base for diverse engineering roles
ROLE_SKILLS_CATALOG = {
    "frontend": {
        "title": "Frontend Developer",
        "keywords": ["front", "react", "vue", "angular", "web", "ui", "javascript", "typescript", "next", "html"],
        "programming": [
            "JavaScript (ES6+)", "TypeScript", "HTML5", "CSS3 / Modern CSS", "React",
            "Vue.js", "Angular", "Next.js", "Redux / Redux Toolkit", "Zustand",
            "Tailwind CSS", "SASS / SCSS", "Vite", "Webpack", "Responsive Design",
            "REST API Integration", "GraphQL", "WebSockets"
        ],
        "databases": ["REST API / Backend integration", "Firebase / Supabase", "Local Storage / IndexedDB"],
        "tools": ["Git", "GitHub / GitLab", "npm / yarn / pnpm", "VS Code", "Figma", "Chrome DevTools", "Postman / Bruno", "Vercel / Netlify", "Jest / Vitest", "CI/CD basics"]
    },
    "backend_python": {
        "title": "Backend Python Developer",
        "keywords": ["python", "django", "fastapi", "flask"],
        "programming": [
            "Python 3", "FastAPI", "Django", "Django REST Framework", "Flask",
            "AsyncIO", "Pydantic", "SQLAlchemy", "Celery", "RESTful API Design",
            "gRPC / Protocol Buffers", "Microservices Architecture", "Pytest / Unit Testing"
        ],
        "databases": ["PostgreSQL", "Redis", "MySQL", "MongoDB", "Elasticsearch", "SQL / Database Indexing"],
        "tools": ["Git", "GitHub / GitLab", "Docker", "Docker Compose", "Linux (Bash)", "CI/CD (GitHub Actions / GitLab CI)", "Postman / Bruno", "Nginx", "AWS / GCP basics"]
    },
    "backend_node": {
        "title": "Backend Node.js / TypeScript Developer",
        "keywords": ["node", "nest", "express", "backend ts", "backend js"],
        "programming": [
            "Node.js", "TypeScript", "JavaScript", "NestJS", "Express.js",
            "REST API Design", "GraphQL", "JWT / Authentication", "Microservices",
            "Jest / Supertest", "Socket.io / WebSockets", "Event-Driven Architecture"
        ],
        "databases": ["PostgreSQL", "Prisma ORM", "TypeORM", "MongoDB", "Redis", "SQL"],
        "tools": ["Git", "GitHub / GitLab", "npm / pnpm", "Docker", "Docker Compose", "Linux", "CI/CD", "Postman / Bruno", "Swagger / OpenAPI"]
    },
    "backend_java": {
        "title": "Java / Spring Boot Developer",
        "keywords": ["java", "spring", "kotlin"],
        "programming": [
            "Java (11/17/21)", "Spring Boot", "Spring MVC", "Spring Security", "Spring Data JPA",
            "Kotlin", "RESTful Web Services", "Hibernate / JPA", "JUnit / Mockito",
            "Microservices Architecture", "Apache Kafka / RabbitMQ"
        ],
        "databases": ["PostgreSQL", "MySQL", "Oracle Database", "Redis", "Liquibase / Flyway"],
        "tools": ["Git", "Maven", "Gradle", "Docker", "Kubernetes basics", "IntelliJ IDEA", "Linux", "CI/CD"]
    },
    "backend_go": {
        "title": "Go / Golang Developer",
        "keywords": ["go", "golang"],
        "programming": [
            "Go (Golang)", "Goroutines & Channels", "Gin / Echo / Fiber", "gRPC & Protobuf",
            "REST API Architecture", "Microservices", "Unit & Benchmark Testing in Go", "Concurrency patterns"
        ],
        "databases": ["PostgreSQL", "Redis", "MongoDB", "GORM / sqlx", "Kafka / RabbitMQ"],
        "tools": ["Git", "Docker", "Docker Compose", "Kubernetes", "Linux", "Prometheus & Grafana", "CI/CD"]
    },
    "fullstack": {
        "title": "Fullstack Developer",
        "keywords": ["fullstack", "full stack", "full-stack", "mern", "mean"],
        "programming": [
            "TypeScript", "JavaScript", "React", "Next.js", "Node.js",
            "Python / FastAPI", "HTML5 & CSS3 / Tailwind", "REST APIs", "GraphQL",
            "State Management (Zustand / Redux)", "Authentication (JWT / OAuth)"
        ],
        "databases": ["PostgreSQL", "Prisma / SQLAlchemy", "MongoDB", "Redis", "SQL"],
        "tools": ["Git", "GitHub", "Docker", "Docker Compose", "Linux", "Vercel / Railway", "Postman", "CI/CD basics"]
    },
    "devops": {
        "title": "DevOps / Infrastructure Engineer",
        "keywords": ["devops", "sre", "cloud", "infra", "sysadmin", "infrastructure"],
        "programming": ["Bash / Shell Scripting", "Python for Automation", "Go basics", "Infrastructure as Code"],
        "databases": ["PostgreSQL administration", "Redis", "Database Backup & Replication"],
        "tools": [
            "Linux / Unix System Administration", "Docker", "Docker Compose", "Kubernetes (K8s)",
            "Terraform", "Ansible", "CI/CD (GitHub Actions / GitLab CI)", "Helm",
            "AWS / GCP / Azure", "Prometheus & Grafana", "Nginx / Reverse Proxy", "Git / GitHub"
        ]
    },
    "qa": {
        "title": "QA / Test Automation Engineer",
        "keywords": ["qa", "tester", "quality", "automation", "test"],
        "programming": [
            "Test Automation (Python / JavaScript / TypeScript)", "Playwright", "Cypress",
            "Selenium WebDriver", "API Testing (Postman / REST Assured)", "Manual Testing & Test Plans"
        ],
        "databases": ["SQL for Data Validation", "PostgreSQL basics"],
        "tools": ["Git", "GitHub / GitLab", "Jira / TestRail", "Postman / Bruno", "Docker basics", "CI/CD test pipelines"]
    },
    "data": {
        "title": "Data Analyst / Data Scientist",
        "keywords": ["data", "ml", "machine learning", "analytics", "analyst", "ai"],
        "programming": [
            "Python", "Pandas", "NumPy", "SQL (Advanced)", "Scikit-learn",
            "Data Visualization (Matplotlib / Seaborn / Plotly)", "Jupyter Notebooks", "REST APIs"
        ],
        "databases": ["PostgreSQL", "ClickHouse / BigQuery / Snowflake", "Redis / MongoDB"],
        "tools": ["Git", "GitHub", "Docker", "Airflow / Prefect", "Tableau / Power BI / Metabase", "Linux"]
    }
}

DEFAULT_UNIVERSAL_SKILLS = {
    "programming": [
        "Python", "JavaScript", "TypeScript", "REST API Design",
        "Object-Oriented Programming (OOP)", "Unit Testing & Debugging"
    ],
    "databases": ["SQL", "PostgreSQL", "Database Design & Queries"],
    "tools": ["Git", "GitHub", "Docker basics", "Linux / Command Line", "VS Code", "Agile / Scrum principles"]
}


def ask_input(prompt: str, default: str = "", required: bool = False) -> str:
    """Prompt user with default value and optional required validation."""
    suffix = f" [{default}]" if default else ""
    while True:
        try:
            val = input(f"{prompt}{suffix}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nНастройка отменена пользователем.")
            sys.exit(0)
        if not val and default:
            return default
        if val:
            return val
        if not required:
            return ""
        print("  ⚠️ Это поле обязательно. Пожалуйста, введите значение.")


def choose_option(prompt: str, options: list[tuple[str, str]], default_index: int = 0) -> str:
    """Prompt user to choose one of numbered options."""
    print(f"\n{prompt}")
    for idx, (label, _) in enumerate(options, 1):
        def_tag = " (по умолчанию)" if idx - 1 == default_index else ""
        print(f"  [{idx}] {label}{def_tag}")
    while True:
        try:
            choice = input(f"Выберите вариант [1-{len(options)}] [{default_index + 1}]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nНастройка отменена.")
            sys.exit(0)
        if not choice:
            return options[default_index][1]
        if choice.isdigit():
            c = int(choice)
            if 1 <= c <= len(options):
                return options[c - 1][1]
        print(f"  ⚠️ Введите число от 1 до {len(options)}.")


def find_skills_for_role(role_title: str) -> dict:
    """Find appropriate skill set based on role title matching."""
    role_lower = role_title.lower()
    for _, track in ROLE_SKILLS_CATALOG.items():
        if any(kw in role_lower for kw in track["keywords"]):
            return track
    return {
        "title": role_title,
        "keywords": [role_lower],
        "programming": DEFAULT_UNIVERSAL_SKILLS["programming"],
        "databases": DEFAULT_UNIVERSAL_SKILLS["databases"],
        "tools": DEFAULT_UNIVERSAL_SKILLS["tools"]
    }


def generate_skills_checklist(role_title: str, candidate_name: str) -> Path:
    """Generate skills_checklist.md customized to the candidate's target role."""
    matched = find_skills_for_role(role_title)
    
    content = f"""# Чек-лист навыков / Skills Checklist
# Кандидат: {candidate_name}
# Желаемая должность: {role_title}
# -----------------------------------------------------------------------------
# ИНСТРУКЦИЯ:
# Отметьте навыки, которыми вы владеете:
# Замените `[ ]` на `[x]` ИЛИ `n` на `y` в конце строки напротив ваших навыков.
#
# Пример:
#   - [x] TypeScript (y)
#   - [ ] Ruby (n)
#
# Вы можете добавить любые свои навыки в соответствующие разделы списка!
# Сохраните этот файл, затем в консоли мастера нажмите Enter.
# -----------------------------------------------------------------------------

## Языки программирования, фреймворки и архитектура
"""
    for sk in matched.get("programming", []):
        content += f"- [ ] {sk} (y/n)\n"

    content += "\n## Базы данных и хранилища\n"
    for sk in matched.get("databases", []):
        content += f"- [ ] {sk} (y/n)\n"

    content += "\n## Инструменты, платформы и окружение\n"
    for sk in matched.get("tools", []):
        content += f"- [ ] {sk} (y/n)\n"

    content += """
## Дополнительные / исключённые технологии
<!-- Напишите технологии, которые вы НЕ хотите использовать или НЕ знаете, через запятую: -->
- **Excluded (не предлагать вакансии с ними):** 
"""
    CHECKLIST_FILE.write_text(content, encoding="utf-8")
    return CHECKLIST_FILE


def parse_skills_checklist() -> dict:
    """Parse marked skills from skills_checklist.md."""
    if not CHECKLIST_FILE.is_file():
        return {"programming": [], "databases": [], "tools": [], "all_confirmed": [], "excluded": []}

    text = CHECKLIST_FILE.read_text(encoding="utf-8")
    
    current_section = "programming"
    skills = {
        "programming": [],
        "databases": [],
        "tools": [],
        "all_confirmed": [],
        "excluded": []
    }

    for line in text.splitlines():
        line_clean = line.strip()
        
        # Section detection
        if "## Языки программирования" in line_clean or "## Programming" in line_clean:
            current_section = "programming"
            continue
        elif "## Базы данных" in line_clean or "## Databases" in line_clean:
            current_section = "databases"
            continue
        elif "## Инструменты" in line_clean or "## Tools" in line_clean:
            current_section = "tools"
            continue
        elif "## Дополнительные" in line_clean or "Excluded" in line_clean:
            current_section = "excluded"

        if current_section == "excluded":
            if "- **Excluded" in line_clean:
                excl_part = line_clean.split(":", 1)[-1].strip()
                if excl_part:
                    skills["excluded"] = [e.strip() for e in excl_part.split(",") if e.strip()]
            continue

        # Check for marked item
        # Matches: - [x] Skill, - [X] Skill, - [ ] Skill (y), - [ ] Skill y
        if line_clean.startswith("- ["):
            is_checked = False
            # Checkbox [x] or [X]
            if re.match(r"^-\s*\[[xX]\]", line_clean):
                is_checked = True
            # (y) or (Y) or 'y' at end
            elif re.search(r"\(\s*[yY]\s*\)|\s+[yY]$", line_clean):
                is_checked = True
            
            if is_checked:
                # Extract skill name
                name_match = re.match(r"^-\s*\[[xX\s]\]\s*([^(]+?)(?:\s*\([yYnN/ ]+\)|\s+[yYnN])?$", line_clean)
                if name_match:
                    name = name_match.group(1).strip()
                    if name and name not in skills["all_confirmed"]:
                        skills[current_section].append(name)
                        skills["all_confirmed"].append(name)

    return skills


def update_profile_files(data: dict, skills_data: dict) -> None:
    """Populate canonical profile files with candidate identity and verified skills."""
    name = data.get("name", "Candidate")
    location = data.get("location", "")
    phone = data.get("phone", "")
    email = data.get("email", "")
    role = data.get("role", "Developer")
    work_type = data.get("work_type", "Remote / Hybrid / Office")
    constraints = data.get("constraints", "")
    salary = data.get("salary", "")
    languages_str = data.get("languages", "English (B2)")
    linkedin = data.get("linkedin", "")
    github = data.get("github", "")
    portfolio = data.get("portfolio", "")

    # Combine constraints
    combined_constraints = []
    if work_type:
        combined_constraints.append(f"Format: {work_type}")
    if constraints:
        combined_constraints.append(constraints)
    if salary:
        combined_constraints.append(f"Min compensation: {salary}")
    full_constraints_str = "; ".join(combined_constraints) if combined_constraints else "Standard employment"

    # 1. Update 01-candidate-profile.md
    if PROFILE_01.is_file():
        p1 = PROFILE_01.read_text(encoding="utf-8")
        p1 = re.sub(r"^-\s+\*\*Name:\*\*.*$", f"- **Name:** {name}", p1, flags=re.MULTILINE)
        p1 = re.sub(r"^-\s+\*\*Location:\*\*.*$", f"- **Location:** {location}", p1, flags=re.MULTILINE)
        p1 = re.sub(r"^-\s+\*\*Phone:\*\*.*$", f"- **Phone:** {phone if phone else '[NOT_PROVIDED]'}", p1, flags=re.MULTILINE)
        p1 = re.sub(r"^-\s+\*\*Email:\*\*.*$", f"- **Email:** {email}", p1, flags=re.MULTILINE)
        p1 = re.sub(r"^-\s+\*\*LinkedIn:\*\*.*$", f"- **LinkedIn:** {linkedin if linkedin else '[NOT_PROVIDED]'}", p1, flags=re.MULTILINE)
        p1 = re.sub(r"^-\s+\*\*GitHub:\*\*.*$", f"- **GitHub:** {github if github else '[NOT_PROVIDED]'}", p1, flags=re.MULTILINE)
        p1 = re.sub(r"^-\s+\*\*Portfolio:\*\*.*$", f"- **Portfolio:** {portfolio if portfolio else '[NOT_PROVIDED]'}", p1, flags=re.MULTILINE)
        p1 = re.sub(r"^-\s+\*\*Status:\*\*.*$", f"- **Status:** Actively looking for a position ({role})", p1, flags=re.MULTILINE)
        p1 = re.sub(r"^-\s+\*\*Constraints:\*\*.*$", f"- **Constraints:** {full_constraints_str}", p1, flags=re.MULTILINE)

        # Update Languages table
        lang_rows = []
        for l_item in languages_str.split(","):
            l_clean = l_item.strip()
            if not l_clean:
                continue
            # Extract language and level if formatted like "English (B2)"
            lvl_match = re.match(r"^([^(]+)(?:\((.*?)\))?$", l_clean)
            if lvl_match:
                lang_name = lvl_match.group(1).strip()
                lang_lvl = lvl_match.group(2).strip() if lvl_match.group(2) else "Working proficiency"
                lang_rows.append(f"| {lang_name} | {lang_lvl} | Verified proficiency |")
        
        if lang_rows:
            lang_table = "| Language | Level | Notes |\n|----------|-------|-------|\n" + "\n".join(lang_rows)
            p1 = re.sub(r"### Languages.*?\n(\|.*?)(?=\n## |\Z)", f"### Languages\n{lang_table}\n\n", p1, flags=re.DOTALL)

        # Update Technical Skills
        prog_skills = ", ".join(skills_data.get("programming", [])) or "Core development skills"
        db_skills = ", ".join(skills_data.get("databases", [])) or "Relational / NoSQL databases"
        tools_skills = ", ".join(skills_data.get("tools", [])) or "Git, VS Code"
        excl_str = ", ".join(skills_data.get("excluded", [])) or "None specified"

        tech_section = f"""## Technical Skills

### Core & Programming
- **Confirmed:** {prog_skills}

### Databases & Storage
- **Confirmed:** {db_skills}

### Tools & Platforms
- **Confirmed:** {tools_skills}

### Excluded Technologies
- {excl_str}
"""
        p1 = re.sub(r"## Technical Skills.*?(?=\n## Publications|\n## Awards|\n## References|\Z)", tech_section + "\n", p1, flags=re.DOTALL)
        PROFILE_01.write_text(p1, encoding="utf-8")

    # 2. Update 02-behavioral-profile.md
    if BEHAVIORAL_02.is_file():
        p2 = BEHAVIORAL_02.read_text(encoding="utf-8")
        overview_text = f"{name} is an active and focused professional targeting {role} roles. Demonstrates solid initiative, practical implementation focus, and team collaboration readiness."
        p2 = re.sub(r"## Overview\s*\n+.*?(?=\n## |\Z)", f"## Overview\n{overview_text}\n\n", p2, flags=re.DOTALL)
        BEHAVIORAL_02.write_text(p2, encoding="utf-8")

    # 3. Update 04-job-evaluation.md
    if EVALUATION_04.is_file():
        p4 = EVALUATION_04.read_text(encoding="utf-8")
        p4 = re.sub(r"\[TARGET_ROLE\]|\[ROLE\]", role, p4)
        p4 = re.sub(r"\[TARGET_LOCATION\]|\[LOCATION\]", location, p4)
        EVALUATION_04.write_text(p4, encoding="utf-8")

    # 4. Update cv/main_example.tex
    if CV_FILE.is_file():
        cv_text = CV_FILE.read_text(encoding="utf-8")
        name_parts = name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        cv_text = re.sub(r"\\name\{.*?\}\{.*?\}", f"\\name{{{first_name}}}{{{last_name}}}", cv_text)
        cv_text = re.sub(r"\\address\{.*?\}\{.*?\}\{.*?\}", f"\\address{{{location}}}{{}}{{}}", cv_text)
        cv_text = re.sub(r"\\email\{.*?\}", f"\\email{{{email}}}", cv_text)
        
        # Update competencies summary in CV
        all_confirmed = skills_data.get("all_confirmed", [])
        if all_confirmed:
            competencies_str = ", ".join(all_confirmed[:12])
            cv_text = re.sub(r"\\item \\textbf\{Core Competencies\}:.*", f"\\item \\textbf{{Core Competencies}}: {competencies_str}", cv_text)
            
        CV_FILE.write_text(cv_text, encoding="utf-8")

    # 5. Update search-queries.md
    if QUERIES_FILE.is_file():
        q_text = QUERIES_FILE.read_text(encoding="utf-8")
        q_text = re.sub(r"\[ROLE_1\]|\[PRIMARY_ROLE\]", role, q_text)
        q_text = re.sub(r"\[CITY_1\]|\[LOCATION\]", location, q_text)
        QUERIES_FILE.write_text(q_text, encoding="utf-8")

    # Mark setup as completed
    CONFIGURED_MARKER.write_text(f"setup_date={import_datetime_now()}\ncandidate={name}\nrole={role}\n", encoding="utf-8")


def import_datetime_now() -> str:
    from datetime import datetime
    return datetime.now().isoformat()


def is_setup_completed() -> bool:
    """Check if the candidate profile has already been onboarded."""
    if CONFIGURED_MARKER.is_file():
        return True
    if PROFILE_01.is_file():
        text = PROFILE_01.read_text(encoding="utf-8")
        if "[YOUR_NAME]" not in text and "- **Name:**" in text:
            # Check if name is non-empty and non-placeholder
            m = re.search(r"^-\s+\*\*Name:\*\*\s*(.+)$", text, re.MULTILINE)
            if m and m.group(1).strip() and not m.group(1).strip().startswith("["):
                return True
    return False


def run_wizard():
    """Run full interactive CLI onboarding session."""
    print("\n" + "=" * 65)
    print("  🚀 Мастер первичной настройки AI Job Search Assistant")
    print("=" * 65)
    print("Добро пожаловать! Давайте настроим ваш профиль поиска работы.")
    print("Все данные сохраняются локально в canonical-файлах проекта.\n")

    # Step 1: Collect Candidate Information
    print("--- Шаг 1/3: Основная информация о вас ---")
    name = ask_input("Имя и Фамилия", default="", required=True)
    location = ask_input("Город и страна проживания (напр. Warsaw, Poland)", default="", required=True)
    email = ask_input("Контактный Email", default="", required=True)
    phone = ask_input("Телефон (опционально)", default="")
    
    role = ask_input("Желаемая должность / роль (напр. Frontend Developer, Python Backend)", default="Frontend Developer", required=True)
    
    work_type = choose_option(
        "Предпочитаемый формат работы:",
        [
            ("Удалённо (Remote)", "Remote"),
            ("Гибрид (Hybrid)", "Hybrid"),
            ("В офисе (Office)", "Office"),
            ("Любой подходящий (Remote / Hybrid / Office)", "Remote / Hybrid / Office"),
        ],
        default_index=0
    )

    constraints = ask_input("Ограничения по поездкам / локации (напр. Только удалённо или в пределах города)", default="Remote or Local")
    salary = ask_input("Минимальный желаемый уровень оплаты (напр. 7000 PLN / 2000 USD)", default="")
    languages = ask_input("Языки и уровни владения через запятую (напр. English (B2), Russian (Native))", default="English (B2)", required=True)

    print("\n--- Ссылки (необязательно, можно пропустить) ---")
    github = ask_input("GitHub профиль (напр. https://github.com/username)", default="")
    linkedin = ask_input("LinkedIn профиль (напр. https://linkedin.com/in/username)", default="")
    portfolio = ask_input("Портфолио / сайт", default="")

    candidate_data = {
        "name": name,
        "location": location,
        "email": email,
        "phone": phone,
        "role": role,
        "work_type": work_type,
        "constraints": constraints,
        "salary": salary,
        "languages": languages,
        "github": github,
        "linkedin": linkedin,
        "portfolio": portfolio,
    }

    # Step 2: Generate Skills Checklist
    print("\n" + "-" * 65)
    print("--- Шаг 2/3: Генерация чек-листа навыков под вашу должность ---")
    checklist_path = generate_skills_checklist(role, name)
    print(f"✅ Файл сгенерирован: {checklist_path.name}")
    print("\n💡 Что делать дальше:")
    print(f"  1. Откройте файл '{checklist_path.name}' в любом текстовом редакторе (VS Code, Notepad, etc.).")
    print("  2. Отметьте навыки, которыми владеете: замените [ ] на [x] или добавьте 'y' напротив навыка.")
    print("  3. Сохраните файл.")
    print("  4. Вернитесь сюда и нажмите Enter для применения отмеченных скиллов.")
    
    input("\n👉 Нажмите [Enter], когда отметите навыки в файле (или сразу для авто-продолжения)... ")

    # Step 3: Apply Skills and Finalize
    print("\n--- Шаг 3/3: Синхронизация профиля ---")
    skills_data = parse_skills_checklist()
    confirmed_count = len(skills_data.get("all_confirmed", []))
    print(f"📋 Распознано отмеченных навыков: {confirmed_count}")
    if confirmed_count > 0:
        sample_skills = ", ".join(skills_data["all_confirmed"][:6])
        print(f"   (Среди них: {sample_skills}{'...' if confirmed_count > 6 else ''})")
    else:
        print("   (Навыки не были отмечены вручную; использован базовый стек для вашей роли)")
        matched = find_skills_for_role(role)
        skills_data["programming"] = matched.get("programming", [])[:5]
        skills_data["databases"] = matched.get("databases", [])[:2]
        skills_data["tools"] = matched.get("tools", [])[:4]
        skills_data["all_confirmed"] = skills_data["programming"] + skills_data["databases"] + skills_data["tools"]

    update_profile_files(candidate_data, skills_data)
    print("\n" + "=" * 65)
    print("🎉 Настройка успешно завершена!")
    print("=" * 65)
    print("Обновлены канонические файлы профиля:")
    print(f"  - .claude/skills/job-application-assistant/01-candidate-profile.md")
    print(f"  - .claude/skills/job-application-assistant/02-behavioral-profile.md")
    print(f"  - .claude/skills/job-application-assistant/04-job-evaluation.md")
    print(f"  - .claude/skills/job-scraper/search-queries.md")
    print(f"  - cv/main_example.tex")
    print("\nТеперь вы можете запускать Web UI интерфейс:")
    print("  python app.py")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Job Search Setup Wizard")
    parser.add_argument("--apply-skills", action="store_true", help="Apply skills from existing skills_checklist.md")
    parser.add_argument("--check", action="store_true", help="Check if setup has been completed")
    args = parser.parse_args()

    if args.check:
        if is_setup_completed():
            print("Setup status: COMPLETED")
            sys.exit(0)
        else:
            print("Setup status: PENDING")
            sys.exit(1)

    if args.apply_skills:
        print("Синхронизация навыков из skills_checklist.md...")
        skills = parse_skills_checklist()
        from services.candidate_service import get_canonical_profile
        profile = get_canonical_profile()
        identity = profile.get("identity", {})
        update_profile_files(
            {
                "name": identity.get("name", "Candidate"),
                "location": identity.get("location", ""),
                "email": identity.get("email", ""),
                "phone": identity.get("phone", ""),
                "role": profile.get("preferred_roles", ["Developer"])[0],
                "languages": ", ".join(l["language"] for l in profile.get("languages", [])),
                "work_type": identity.get("constraints", ""),
            },
            skills
        )
        print(f"✅ Успешно обновлено! Подтверждено навыков: {len(skills.get('all_confirmed', []))}")
        sys.exit(0)

    run_wizard()
