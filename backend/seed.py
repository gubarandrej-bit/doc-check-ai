# seed.py
import datetime
from models import NtdDocument, User, AiModel, SessionLocal
from auth import get_password_hash

NTD_LIST = [
    ("123-ФЗ", "Технический регламент о требованиях пожарной безопасности", "ФЗ", datetime.datetime(2008, 7, 22)),
    ("СП 3.13130.2009", "Системы противопожарной защиты. Система оповещения и управления эвакуацией людей при пожаре. Требования пожарной безопасности", "СП", datetime.datetime(2009, 3, 4)),
    ("СП 6.13130.2021", "Системы противопожарной защиты. Электроустановки низковольтные. Требования пожарной безопасности", "СП", datetime.datetime(2021, 1, 1)),
    ("СП 76.13330.2016", "Электротехнические устройства. Актуализированная редакция СНиП 3.05.06-85", "СП", datetime.datetime(2016, 1, 1)),
    ("СП 484.1311500.2020", "Системы противопожарной защиты. Системы пожарной сигнализация и автоматизация систем противопожарной защиты. Нормы и правила проектирования", "СП", datetime.datetime(2020, 1, 1)),
    ("СП 486.1311500.2020", "Системы противопожарной защиты. Перечень зданий, сооружений, помещений и оборудования, подлежащих защите автоматическими установками пожаротушения и системами пожарной сигнализации. Нормы и правила проектирования", "СП", datetime.datetime(2020, 1, 1)),
    ("ПУЭ-7", "Правила устройства электроустановок. Изд. 7", "ПУЭ", datetime.datetime(2005, 1, 1)),
    ("ГОСТ 21.208-2013", "СПДС. Автоматизация технологических процессов. Обозначения условные приборов и средств автоматизации в схемах", "ГОСТ", datetime.datetime(2013, 1, 1)),
    ("ГОСТ Р 21.101-2026", "Система проектной документации для строительства. Основные требования к проектной и рабочей документации", "ГОСТ", datetime.datetime(2026, 1, 1)),
    ("ГОСТ 21.210-2014", "СПДС. Условные графические изображения электрооборудования и проводок на планах", "ГОСТ", datetime.datetime(2014, 1, 1)),
    ("ГОСТ Р 21.703-2020", "СПДС. Правила выполнения рабочей документации проводных средств связи", "ГОСТ", datetime.datetime(2020, 1, 1)),
    ("ГОСТ 31565-2012", "Кабельные изделия. Требования пожарной безопасности", "ГОСТ", datetime.datetime(2012, 1, 1)),
    ("ГОСТ Р 53246-2025", "Информационные технологии. Системы кабельные структурированные. Проектирование основных узлов системы. Общие требования", "ГОСТ", datetime.datetime(2025, 1, 1)),
    ("ГОСТ Р 58238-2018", "Слаботочные системы. Кабельные систем��. Порядок и нормы проектирования. Общие положения", "ГОСТ", datetime.datetime(2018, 1, 1)),
    ("СП 48.13330.2019", "СНИП 12-01-2004 Организация строительства", "СП", datetime.datetime(2019, 1, 1)),
]

def seed_ntd(session):
    if session.query(NtdDocument).count() > 0:
        return
    for number, title, dtype, eff in NTD_LIST:
        session.add(NtdDocument(
            number=number, title=title, doc_type=dtype,
            effective_date=eff, status="actual", url="",
            note="Скопировать актуальную редакцию с официального сайта перед использованием.",
        ))

def seed_default_admin(session):
    if session.query(User).filter_by(login="admin").first():
        return
    session.add(User(
        login="admin", password_hash=get_password_hash("admin123"),
        full_name="Администратор", role="admin", is_active=True,
    ))

def seed_default_models(session):
    if session.query(AiModel).count() > 0:
        return
    session.add(AiModel(name="OpenRouter (бесплатные LLM)", provider="openrouter",
                        model_id="openrouter/free", mode="cloud", is_default=True,
                        description="Бесплатные LLM через OpenRouter для текстового анализа PDF/DOC."))
    session.add(AiModel(name="Ollama llama3.1 (локально)", provider="ollama",
                        model_id="llama3.1:8b", mode="local", is_default=False,
                        description="Локальная модель через Ollama. Требует установки Ollama и загрузки весов."))