# Project Map - AI Context

> **Auto-generated** project cartography for LLM coding agents
> 
> **Stats:** 67 files | 13,525 LOC | 86 classes | 129 functions

---

## Quick Overview

This map provides complete project context for AI pair programming. Use it to understand:
- Project structure and file organization
- Dependencies between modules
- Key classes and their responsibilities
- Database schema (if applicable)

---
## 🏗️ Project Structure

### 📁 `./`

#### `project_mapper_qwenCoder_rev.py` (1840 LOC)

**Purpose:** 3 classes, 26 funcs

**Classes:**
- `FileAnalysis`
- `CacheEntry`
- `CodeAnalyzer` extends ast.NodeVisitor
  - Methods: `__init__()`, `visit_Import()`, `visit_ImportFrom()`, `_is_stdlib()`, `_resolve_internal_import()` (+8 more)

**Functions:**
- `get_file_hash(filepath)`
- `get_changed_files(project_root, ignore_dirs, cache_dir)`
- `get_changed_files_multilang(project_root, ignore_dirs, cache_dir)`
- `load_cached_analysis(filepath, project_root, cache_dir)`
- `load_cached_analysis_multilang(filepath, project_root, cache_dir)`
- `analyze_file_multilang(filepath, project_root, cache_dir)`
- `analyze_file(filepath, project_root, cache_dir)`
- `analyze_project(root_dir, ignore_dirs, cache_dir)`
- ... +18 more functions

**Constants:**
- `YAML_AVAILABLE` = True
- `YAML_AVAILABLE` = False

**Exception Handling:**
- 28 exception handling constructs

**Key imports:** `argparse`, `ast`, `concurrent.futures`, `hashlib`, `json`
 (+16 more)

---

#### `run.py` (7 LOC)

**Purpose:** utility module

**Key imports:** `libapp.app`

---

### 📁 `alembic/`

#### `env.py` (45 LOC)

**Purpose:** 2 funcs

**Functions:**
- `run_migrations_offline()`
- `run_migrations_online()`

**Key imports:** `os`, `sys`, `logging.config`, `sqlalchemy`, `alembic`
 (+2 more)

---

### 📁 `alembic\versions/`

#### `85242b1a76fb_add_title_and_author_indexes_to_books_.py` (32 LOC)

**Purpose:** 2 funcs

**Functions:**
- `upgrade()`
- `downgrade()`

**Key imports:** `collections.abc`, `alembic`

---

### 📁 `libapp/`

#### `__version__.py` (16 LOC)

**Purpose:** utility module

---

#### `app.py` (755 LOC)

**Purpose:** 1 class, 1 func

**Classes:**
- `MainWindow` extends QMainWindow
  - Methods: `__init__()`, `_check_overdue_on_startup()`, `_show_overdues_from_alert()`, `_load_config_and_translate()`, `_create_actions()` (+32 more)

**Functions:**
- `main()`

**Exception Handling:**
- 2 exception handling constructs

**Key imports:** `__future__`, `logging`, `sys`, `qdarktheme`, `PySide6.QtCore`
 (+27 more)

---

### 📁 `libapp\persistence/`

#### `base.py` (18 LOC)

**Purpose:** 1 class

**Classes:**
- `Base` extends DeclarativeBase

**Key imports:** `__future__`, `sqlalchemy.orm`

---

#### `database.py` (134 LOC)

**Purpose:** 3 funcs

**Functions:**
- `get_session()`
- `ensure_tables()`
- `_init_db()`

**Constants:**
- `DATABASE_URL` = f'sqlite:///{db_path().as_posix()}'

**Key imports:** `__future__`, `sqlalchemy`, `sqlalchemy.orm`, `libapp.utils.paths`, `base`
 (+2 more)

---

#### `migrate.py` (53 LOC)

**Purpose:** 2 funcs

**Functions:**
- `column_exists(table, col)`
- `upgrade()`

**Key imports:** `__future__`, `sys`, `sqlalchemy`, `libapp.persistence.database`

---

#### `models_sa.py` (217 LOC)

**Purpose:** 8 classes

**Classes:**
- `Author` extends Base
- `MemberStatus` extends str, enum.Enum
- `BookCategory` extends str, enum.Enum
- `LoanStatus` extends str, enum.Enum
- `Book` extends Base
  - Methods: `code()`, `code()`, `author()`, `author()`, `fund()`
- `Member` extends Base
- `Loan` extends Base
- `AuditLog` extends Base
  - Methods: `__repr__()`

**Key imports:** `__future__`, `enum`, `datetime`, `sqlalchemy`, `sqlalchemy.ext.hybrid`
 (+2 more)

---

#### `repositories.py` (118 LOC)

**Purpose:** 3 classes

**Classes:**
- `BookRepository`
  - Methods: `__init__()`, `list()`, `get()`, `add()`, `update()` (+1 more)
- `MemberRepository`
  - Methods: `__init__()`, `list()`, `get()`, `add()`, `update()` (+1 more)
- `LoanRepository`
  - Methods: `__init__()`, `get()`, `add()`, `update()`, `list_open_by_member()` (+1 more)

**Key imports:** `__future__`, `sqlalchemy`, `sqlalchemy.orm`, `models_sa`

---

#### `unit_of_work.py` (81 LOC)

**Purpose:** 1 class

**Classes:**
- `UnitOfWork` extends AbstractContextManager
  - Methods: `__init__()`, `__enter__()`, `__exit__()`, `commit()`, `rollback()`

**Exception Handling:**
- 1 exception handling constructs

**Key imports:** `__future__`, `contextlib`, `database`, `repositories`

---

### 📁 `libapp\services/`

#### `audit_service.py` (249 LOC)

**Purpose:** 2 classes, 12 funcs

**Classes:**
- `AuditAction`
- `AuditEntityType`

**Functions:**
- `log_audit(action, entity_type, entity_id, user, details, level)`
- `audit_book_created(book_id, title, user)`
- `audit_book_updated(book_id, changes, user)`
- `audit_book_deleted(book_id, title, user)`
- `audit_import(count, source, user)`
- `audit_export(count, format, user)`
- `audit_member_created(member_id, name, user)`
- `audit_member_updated(member_id, changes, user)`
- ... +4 more functions

**Constants:**
- `CREATE` = 'CREATE'
- `UPDATE` = 'UPDATE'
- `DELETE` = 'DELETE'
- `IMPORT` = 'IMPORT'
- `EXPORT` = 'EXPORT'
- `LOAN` = 'LOAN'
- `RETURN` = 'RETURN'
- `SEARCH` = 'SEARCH'
- `BOOK` = 'book'
- `MEMBER` = 'member'
 (+1 more)

**Exception Handling:**
- 1 exception handling constructs

**Key imports:** `json`, `logging`, `datetime`, `typing`, `persistence.database`
 (+1 more)

---

#### `backup_service.py` (85 LOC)

**Purpose:** 1 class, 1 func

**Classes:**
- `BackupError` extends Exception

**Functions:**
- `create_backup(backup_folder)`

**Exception Handling:**
- 3 exception handling constructs

**Key imports:** `__future__`, `logging`, `shutil`, `datetime`, `pathlib`
 (+1 more)

---

#### `bnf_adapter.py` (122 LOC)

**Purpose:** 1 class, 3 funcs

**Classes:**
- `BnfAdapter`
  - Methods: `by_isbn()`, `search_title_author()`

**Functions:**
- `_clean_person(s)`
- `_extract_dc_text(elem, tag)`
- `_notice_to_dict(record)`

**Constants:**
- `SRU` = 'https://catalogue.bnf.fr/api/SRU'
- `SCHEMA` = 'dublincore'

**Key imports:** `__future__`, `re`, `xml.etree.ElementTree`, `requests`

---

#### `bnf_service.py` (218 LOC)

**Purpose:** 2 classes, 2 funcs

**Classes:**
- `BnfBook`
- `BnfService`
  - Methods: `__init__()`, `search_by_isbn()`, `search_by_title_author()`, `_search_sru()`, `_parse_intermarc()`

**Functions:**
- `first_text(codes)`
- `all_texts(codes)`

**Constants:**
- `BASE` = 'https://catalogue.bnf.fr/api/SRU'

**Exception Handling:**
- 4 exception handling constructs

**Key imports:** `__future__`, `urllib.parse`, `urllib.request`, `xml.etree.ElementTree`, `dataclasses`
 (+2 more)

---

#### `book_service.py` (127 LOC)

**Purpose:** 2 classes

**Classes:**
- `BookDTO`
- `BookService`
  - Methods: `__init__()`, `list()`, `create()`, `update()`, `delete()`

**Exception Handling:**
- 3 exception handling constructs

**Key imports:** `__future__`, `logging`, `dataclasses`, `persistence.models_sa`, `persistence.unit_of_work`

---

#### `column_mapping.py` (167 LOC)

**Purpose:** 4 funcs

**Functions:**
- `load_field_keywords()`
- `calculate_similarity_score(field_keywords, column_name)`
- `normalize_text(text)`
- `suggest_column_mapping(column_names, db_fields)`

**Constants:**
- `DEFAULT_FIELD_KEYWORDS` = {'title': ['titre', 'title', 'book', 'livre', 'nom', 'name', 'ouvrage', 'designation'], 'author': ['auteur', 'author', 'auteur(s)', 'authors', 'écrivain', 'writer', 'creator'], 'isbn': ['isbn', 'isbn13', 'isbn10', 'ean', 'code_barre', 'barcode', 'code'], 'year': ['année', 'year', 'date', 'an', 'annee', 'edition', 'parution', 'published'], 'publisher': ['éditeur', 'publisher', 'maison', 'edition', 'editeur', 'press'], 'code': ['code', 'ref', 'référence', 'reference', 'id', 'numéro', 'num', 'identifier'], 'volume': ['volume', 'tome', 'vol', 'number', 'numero', 'n°', 'part'], 'fund': ['fonds', 'fund', 'collection', 'série', 'serie', 'series'], 'copies_total': ['exemplaires', 'copies', 'total', 'quantité', 'qte', 'quantity', 'stock'], 'copies_available': ['disponibles', 'available', 'libre', 'dispo', 'free', 'libres']}
- `FIELD_KEYWORDS` = load_field_keywords()

**Exception Handling:**
- 1 exception handling constructs

**Key imports:** `__future__`, `json`, `logging`, `re`, `difflib`
 (+1 more)

---

#### `config_service.py` (62 LOC)

**Purpose:** 1 class, 3 funcs

**Classes:**
- `AppConfig`

**Functions:**
- `get_config_path()`
- `load_config()`
- `save_config(config)`

**Exception Handling:**
- 2 exception handling constructs

**Key imports:** `json`, `logging`, `dataclasses`, `libapp.utils.paths`

---

#### `enhanced_logging_config.py` (189 LOC)

**Purpose:** 5 funcs

**Functions:**
- `setup_session_logging(max_files, console_output, log_level)`
- `cleanup_old_logs(logs_dir, max_files)`
- `get_current_session_logs(logs_dir)`
- `log_session_info()`
- `setup_app_logging(console_output, max_log_files)`

**Exception Handling:**
- 4 exception handling constructs

**Key imports:** `glob`, `logging`, `logging.handlers`, `os`, `datetime`
 (+5 more)

---

#### `export_service.py` (222 LOC)

**Purpose:** 1 class, 3 funcs

**Classes:**
- `ExportMetadata`
  - Methods: `__init__()`, `generate_lines()`

**Functions:**
- `export_data_to_csv(filepath, headers, data, metadata)`
- `export_data_to_xlsx(filepath, headers, data, metadata, sheet_name)`
- `export_data(filepath, headers, data, file_format, metadata, sheet_name)`

**Exception Handling:**
- 2 exception handling constructs

**Key imports:** `__future__`, `csv`, `collections.abc`, `datetime`, `pathlib`
 (+5 more)

---

#### `googlebooks_service.py` (152 LOC)

**Purpose:** 3 classes

**Classes:**
- `GoogleBooksServiceError` extends Exception
- `GoogleBooksAdapter`
  - Methods: `__init__()`, `to_book_dto()`, `_get_isbn()`, `_get_year()`
- `GoogleBooksService`
  - Methods: `__init__()`, `search_by_isbn()`, `search_by_title_author()`

**Constants:**
- `API_URL` = 'https://www.googleapis.com/books/v1/volumes'

**Exception Handling:**
- 4 exception handling constructs

**Key imports:** `__future__`, `logging`, `requests`, `types`

---

#### `import_service.py` (618 LOC)

**Purpose:** 6 classes, 11 funcs

**Classes:**
- `MappingError` extends Exception
- `BaseImporter` extends Protocol
  - Methods: `extract_rows()`, `map_rows()`
- `CsvImporter`
  - Methods: `extract_rows()`, `map_rows()`
- `ExcelImporter`
  - Methods: `extract_rows()`, `map_rows()`
- `BookRow`
- `MemberRow`

**Functions:**
- `_clean_author(s)`
- `_normalize_isbn(val)`
- `get_importer_for_file(file_path)`
- `_normalize_user_mapping(user_mapping)`
- `parse_xlsx(file_path, mapping_ui)`
- `validate_rows(rows, _progress)`
- `_get_author_objs(session, names)`
- `upsert_rows(rows, on_isbn_conflict, _progress)`
- ... +3 more functions

**Constants:**
- `_FR_REQUIRED` = {'titre'}
- `_FR_OPTIONAL` = {'isbn', 'sous_titre', 'auteurs', 'editeur', 'date_publication', 'collection', 'tome', 'code_interne', 'mots_cles'}
- `_EN_TO_FR` = {'title': 'titre', 'subtitle': 'sous_titre', 'author': 'auteurs', 'authors': 'auteurs', 'isbn': 'isbn', 'publisher': 'editeur', 'year': 'date_publication', 'collection': 'collection', 'fund': 'collection', 'volume': 'tome', 'tome': 'tome', 'code': 'code_interne', 'tags': 'mots_cles'}
- `_MEMBER_EN_TO_FR` = {'member_no': 'numero_membre', 'first_name': 'prenom', 'last_name': 'nom', 'email': 'email', 'phone': 'telephone', 'status': 'statut', 'is_active': 'actif'}
- `_FR_MEMBER_REQUIRED` = {'numero_membre', 'prenom', 'nom'}
- `_FR_MEMBER_OPTIONAL` = {'email', 'telephone', 'statut', 'actif'}

**Exception Handling:**
- 15 exception handling constructs

**Key imports:** `__future__`, `csv`, `logging`, `collections.abc`, `dataclasses`
 (+14 more)

---

#### `loan_service.py` (163 LOC)

**Purpose:** 1 class, 4 funcs

**Classes:**
- `LoanError` extends Exception

**Functions:**
- `is_overdue(due, ret)`
- `create_loan(book_id, member_id, loan_date)`
- `return_loan(loan_id)`
- `get_overdue_count()`

**Exception Handling:**
- 5 exception handling constructs

**Key imports:** `__future__`, `datetime`, `persistence.database`, `persistence.models_sa`, `services.audit_service`
 (+2 more)

---

#### `logging_config.py` (51 LOC)

**Purpose:** 1 func

**Functions:**
- `setup_app_logging(log_level, console_output)`

**Key imports:** `logging`, `logging.handlers`, `utils.paths`

---

#### `member_service.py` (128 LOC)

**Purpose:** 2 classes

**Classes:**
- `MemberDTO`
- `MemberService`
  - Methods: `__init__()`, `list()`, `_ensure_unique_member_no()`, `create()`, `update()` (+1 more)

**Exception Handling:**
- 4 exception handling constructs

**Key imports:** `__future__`, `logging`, `dataclasses`, `persistence.models_sa`, `persistence.unit_of_work`

---

#### `meta_search_service.py` (1143 LOC)

**Purpose:** 12 classes

**Classes:**
- `CacheEntry`
  - Methods: `is_expired()`
- `SimpleCache`
  - Methods: `__init__()`, `get()`, `set()`, `clear()`
- `_SourceMetric`
  - Methods: `duration_ms()`
- `SearchSourceInfo`
- `UnifiedBookResult`
  - Methods: `_calculate_quality_score()`, `score()`, `display_title()`, `authors_display()`, `year_display()` (+1 more)
- `SearchSource` extends Enum
- `SearchResultAdapter`
  - Methods: `from_bnf_book()`, `from_ext_book()`, `from_google_books()`
- `SearchStrategy` extends ABC
  - Methods: `search_by_isbn()`, `search_by_title_author()`
- `SequentialSearchStrategy` extends SearchStrategy
  - Methods: `search_by_isbn()`, `search_by_title_author()`
- `MetaSearchService`
  - Methods: `__init__()`, `search_by_isbn()`, `search_by_title_author()`, `clear_cache()`, `get_cache_stats()` (+1 more)
- `ParallelSearchStrategy` extends SearchStrategy
  - Methods: `__init__()`, `duration_ms()`, `search_by_isbn()`, `search_by_title_author()`, `_search_single_source()`
- `BestResultStrategy` extends SearchStrategy
  - Methods: `__init__()`, `search_by_isbn()`, `search_by_title_author()`, `_deduplicate_results()`, `_normalize_for_deduplication()` (+1 more)

**Constants:**
- `BNF` = 'BnF'
- `GOOGLE_BOOKS` = 'Google Books'
- `OPENLIBRARY` = 'OpenLibrary'

**Exception Handling:**
- 7 exception handling constructs

**Key imports:** `__future__`, `concurrent.futures`, `logging`, `time`, `abc`
 (+8 more)

---

#### `metrics_service.py` (173 LOC)

**Purpose:** 7 funcs

**Functions:**
- `benchmark(operation_name)`
- `decorator(func)`
- `wrapper()`
- `record_metric(operation, duration, success, error, metadata)`
- `save_metrics()`
- `get_metrics_summary()`
- `export_metrics_csv(filepath)`

**Exception Handling:**
- 3 exception handling constructs

**Key imports:** `functools`, `json`, `logging`, `time`, `collections`
 (+5 more)

---

#### `openlibrary_adapter.py` (89 LOC)

**Purpose:** 1 class, 1 func

**Classes:**
- `OpenLibraryAdapter`
  - Methods: `__init__()`, `by_isbn()`

**Functions:**
- `_year_only(val)`

**Constants:**
- `BOOKS_API` = 'https://openlibrary.org/api/books'
- `ISBN_API` = 'https://openlibrary.org/isbn/{isbn}.json'
- `WORKS_API` = 'https://openlibrary.org{path}.json'

**Exception Handling:**
- 3 exception handling constructs

**Key imports:** `__future__`, `typing`, `requests`

---

#### `openlibrary_service.py` (222 LOC)

**Purpose:** 2 classes

**Classes:**
- `ExtBook`
- `OpenLibraryService`
  - Methods: `search_by_isbn()`, `search_by_title()`, `_map_edition()`, `_map()`

**Constants:**
- `BASE` = 'https://openlibrary.org'

**Exception Handling:**
- 4 exception handling constructs

**Key imports:** `__future__`, `dataclasses`, `requests`, `utils`

---

#### `preferences.py` (174 LOC)

**Purpose:** 1 class, 2 funcs

**Classes:**
- `Preferences`
  - Methods: `from_dict()`

**Functions:**
- `load_preferences()`
- `save_preferences(prefs)`

**Exception Handling:**
- 4 exception handling constructs

**Key imports:** `__future__`, `json`, `logging`, `dataclasses`, `typing`
 (+4 more)

---

#### `search_index.py` (55 LOC)

**Purpose:** 1 func

**Functions:**
- `get_suggestions(limit)`

**Exception Handling:**
- 2 exception handling constructs

**Key imports:** `__future__`, `sqlalchemy`, `sqlalchemy.exc`, `libapp.persistence.database`, `libapp.persistence.models_sa`

---

#### `translation_service.py` (111 LOC)

**Purpose:** 1 class, 3 funcs

**Classes:**
- `TranslationService`
  - Methods: `__init__()`, `load_language()`, `set_language()`, `translate()`

**Functions:**
- `get_translation_service()`
- `set_language(language_code)`
- `translate(key)`

**Exception Handling:**
- 2 exception handling constructs

**Key imports:** `__future__`, `logging`, `pathlib`, `typing`, `yaml`

---

#### `types.py` (73 LOC)

**Purpose:** 5 classes

**Classes:**
- `BookRow`
- `BookDTO`
- `ImportErrorItem`
- `ImportBatch`
- `ImportResult`

**Key imports:** `__future__`, `dataclasses`, `typing`

---

#### `utils.py` (112 LOC)

**Purpose:** 5 funcs

**Functions:**
- `clean_author(author_string)`
- `normalize_isbn(isbn)`
- `validate_isbn(isbn)`
- `_validate_isbn10(isbn)`
- `_validate_isbn13(isbn)`

**Key imports:** `__future__`

---

### 📁 `libapp\utils/`

#### `__init__.py` (6 LOC)

**Purpose:** utility module

**Key imports:** `icon_helper`

---

#### `icon_helper.py` (119 LOC)

**Purpose:** 5 funcs

**Functions:**
- `set_current_theme(theme_name)`
- `_get_icon_color(theme_name)`
- `load_icon(name, category, size, theme)`
- `toolbar_icon(name, theme)`
- `app_icon(name, theme)`

**Constants:**
- `_ICON_BASE_PATH` = Path(__file__).parent.parent / 'resources' / 'icons'
- `_CURRENT_THEME` = 'light'
- `_CURRENT_THEME` = theme_name

**Key imports:** `__future__`, `logging`, `pathlib`, `PySide6.QtCore`, `PySide6.QtGui`
 (+2 more)

---

#### `paths.py` (71 LOC)

**Purpose:** 6 funcs

**Functions:**
- `_get_app_dir(roaming)`
- `user_data_dir()`
- `user_config_file()`
- `db_path()`
- `translations_path()`
- `logs_path()`

**Constants:**
- `_APP_NAME` = 'Aurora'
- `_AUTHOR` = '6f4Software'

**Key imports:** `__future__`, `os`, `pathlib`

---

### 📁 `libapp\views/`

#### `__init__.py` (22 LOC)

**Purpose:** utility module

**Key imports:** `__version__`

---

#### `__version__.py` (12 LOC)

**Purpose:** utility module

---

#### `about_dialog.py` (173 LOC)

**Purpose:** 1 class

**Classes:**
- `AboutDialog` extends QDialog
  - Methods: `__init__()`, `_setup_ui()`, `_create_header()`, `_create_content()`, `_create_footer()`

**Key imports:** `__future__`, `PySide6.QtCore`, `PySide6.QtWidgets`, `__version__`, `services.translation_service`
 (+1 more)

---

#### `bnf_select_dialog.py` (106 LOC)

**Purpose:** 1 class

**Classes:**
- `BnfSelectDialog` extends QDialog
  - Methods: `__init__()`, `_on_accept()`

**Key imports:** `__future__`, `PySide6.QtCore`, `PySide6.QtWidgets`, `services.translation_service`

---

#### `book_editor.py` (278 LOC)

**Purpose:** 1 class, 2 funcs

**Classes:**
- `BookEditor` extends QDialog
  - Methods: `__init__()`, `_fill_form_from_book()`, `_on_accept()`, `_apply_if_empty()`, `_on_complete_from_bnf()`

**Functions:**
- `_to_int(val, default)`
- `create_form_row(label, widget)`

**Exception Handling:**
- 2 exception handling constructs

**Key imports:** `__future__`, `typing`, `PySide6.QtWidgets`, `persistence.database`, `persistence.models_sa`
 (+3 more)

---

#### `book_list.py` (839 LOC)

**Purpose:** 2 classes, 2 funcs

**Classes:**
- `BookTableModel` extends QAbstractTableModel
  - Methods: `__init__()`, `set_books()`, `apply_filter()`, `get_book_by_row()`, `rowCount()` (+4 more)
- `BookListView` extends QWidget
  - Methods: `__init__()`, `_setup_ui()`, `_connect_signals()`, `load_view_state()`, `save_view_state()` (+14 more)

**Functions:**
- `is_empty(value)`
- `has_data(value)`

**Constants:**
- `ALL_COLUMNS` = {'id': 'ID', 'code': 'Code', 'title': 'Titre', 'volume': 'Tome', 'author': 'Auteurs', 'year': 'Année', 'isbn': 'ISBN', 'publisher': 'Éditeur', 'fund': 'Fonds', 'available': 'Disponible'}

**Exception Handling:**
- 5 exception handling constructs

**Key imports:** `__future__`, `PySide6.QtCore`, `PySide6.QtWidgets`, `sqlalchemy`, `persistence.database`
 (+17 more)

---

#### `checkout_dialog.py` (208 LOC)

**Purpose:** 1 class

**Classes:**
- `CheckoutDialog` extends QDialog
  - Methods: `__init__()`, `_load_members()`, `_on_member_changed()`, `on_accept()`

**Exception Handling:**
- 1 exception handling constructs

**Key imports:** `__future__`, `datetime`, `PySide6.QtCore`, `PySide6.QtWidgets`, `sqlalchemy`
 (+6 more)

---

#### `dashboard.py` (249 LOC)

**Purpose:** 2 classes, 1 func

**Classes:**
- `ClickableLabel` extends QLabel
  - Methods: `__init__()`, `mousePressEvent()`
- `DashboardView` extends QWidget
  - Methods: `__init__()`, `_setup_ui()`, `_connect_signals()`, `refresh()`, `_update_display()` (+3 more)

**Functions:**
- `_to_int(value)`

**Exception Handling:**
- 2 exception handling constructs

**Key imports:** `__future__`, `datetime`, `functools`, `PySide6.QtCore`, `PySide6.QtWidgets`
 (+5 more)

---

#### `export_dialog.py` (311 LOC)

**Purpose:** 1 class

**Classes:**
- `ExportDialog` extends QDialog
  - Methods: `__init__()`, `_setup_ui()`, `_create_format_section()`, `_create_columns_section()`, `_create_metadata_section()` (+7 more)

**Key imports:** `__future__`, `pathlib`, `typing`, `PySide6.QtWidgets`, `services.translation_service`
 (+1 more)

---

#### `import_dialog.py` (383 LOC)

**Purpose:** 1 class, 1 func

**Classes:**
- `ImportDialog` extends QDialog
  - Methods: `__init__()`, `_setup_ui()`, `_create_file_selection_ui()`, `_create_mapping_ui()`, `_create_options_ui()` (+13 more)

**Functions:**
- `t(key, default)`

**Constants:**
- `BOOK_FIELDS` = ['title', 'author', 'volume', 'year', 'code', 'fund', 'isbn', 'publisher', 'copies_total', 'copies_available']

**Exception Handling:**
- 1 exception handling constructs

**Key imports:** `__future__`, `pathlib`, `pandas`, `PySide6.QtCore`, `PySide6.QtWidgets`
 (+6 more)

---

#### `import_members_dialog.py` (262 LOC)

**Purpose:** 1 class

**Classes:**
- `ImportMembersDialog` extends QDialog
  - Methods: `__init__()`, `_setup_ui()`, `_connect_signals()`, `_on_pick_file()`, `_populate_mapping_combos()` (+2 more)

**Constants:**
- `MEMBER_FIELDS` = ['member_no', 'first_name', 'last_name', 'email', 'phone', 'status', 'is_active']

**Exception Handling:**
- 1 exception handling constructs

**Key imports:** `__future__`, `pathlib`, `pandas`, `PySide6.QtCore`, `PySide6.QtWidgets`
 (+4 more)

---

#### `loan_dialog.py` (187 LOC)

**Purpose:** 1 class

**Classes:**
- `LoanDialog` extends QDialog
  - Methods: `__init__()`, `_load_books()`, `_load_members()`, `_on_accept()`

**Exception Handling:**
- 1 exception handling constructs

**Key imports:** `__future__`, `datetime`, `PySide6.QtCore`, `PySide6.QtWidgets`, `sqlalchemy`
 (+4 more)

---

#### `loan_dialogs.py` (169 LOC)

**Purpose:** 2 classes

**Classes:**
- `NewLoanDialog` extends QDialog
  - Methods: `__init__()`, `_populate_combos()`, `accept()`
- `ReturnLoanDialog` extends QDialog
  - Methods: `__init__()`, `_populate_combo()`, `accept()`

**Exception Handling:**
- 1 exception handling constructs

**Key imports:** `__future__`, `PySide6.QtWidgets`, `sqlalchemy`, `sqlalchemy.orm`, `persistence.database`
 (+3 more)

---

#### `loan_list.py` (448 LOC)

**Purpose:** 2 classes

**Classes:**
- `LoanTableModel` extends QAbstractTableModel
  - Methods: `__init__()`, `get_loan_by_row()`, `set_loans()`, `apply_filters()`, `rowCount()` (+3 more)
- `LoanListView` extends QWidget
  - Methods: `__init__()`, `_setup_ui()`, `_connect_signals()`, `_load_view_state()`, `save_view_state()` (+9 more)

**Constants:**
- `COLUMNS` = ['ID', 'Livre', 'Membre', "Date d'emprunt", "Date d'échéance", 'Statut']

**Exception Handling:**
- 2 exception handling constructs

**Key imports:** `__future__`, `PySide6.QtCore`, `PySide6.QtGui`, `PySide6.QtWidgets`, `sqlalchemy`
 (+11 more)

---

#### `map_columns_dialog.py` (97 LOC)

**Purpose:** 1 class

**Classes:**
- `MapColumnsDialog` extends QDialog
  - Methods: `__init__()`, `_setup_ui()`, `_populate_and_guess_mappings()`

**Key imports:** `__future__`, `PySide6.QtWidgets`, `services.translation_service`

---

#### `member_editor.py` (172 LOC)

**Purpose:** 1 class

**Classes:**
- `MemberEditor` extends QDialog
  - Methods: `__init__()`, `_setup_ui()`, `_connect_signals()`, `_populate_form()`, `accept()`

**Exception Handling:**
- 1 exception handling constructs

**Key imports:** `__future__`, `typing`, `PySide6.QtWidgets`, `sqlalchemy`, `persistence.database`
 (+2 more)

---

#### `member_list.py` (496 LOC)

**Purpose:** 2 classes

**Classes:**
- `MemberTableModel` extends QAbstractTableModel
  - Methods: `__init__()`, `set_members()`, `apply_filter()`, `get_member_by_row()`, `rowCount()` (+4 more)
- `MemberListView` extends QWidget
  - Methods: `__init__()`, `_setup_ui()`, `_connect_signals()`, `load_view_state()`, `save_view_state()` (+10 more)

**Constants:**
- `COLUMNS` = ['ID', 'Numéro de membre', 'Nom', 'Prénom', 'Email', 'Téléphone', 'Statut', 'Actif']

**Exception Handling:**
- 2 exception handling constructs

**Key imports:** `__future__`, `PySide6.QtCore`, `PySide6.QtWidgets`, `sqlalchemy`, `persistence.database`
 (+10 more)

---

#### `natural_sort_proxy.py` (89 LOC)

**Purpose:** 1 class

**Classes:**
- `NaturalSortProxyModel` extends QSortFilterProxyModel
  - Methods: `lessThan()`, `_natural_sort_key()`

**Key imports:** `__future__`, `re`, `PySide6.QtCore`

---

#### `overdue_alert_dialog.py` (81 LOC)

**Purpose:** 1 class

**Classes:**
- `OverdueAlertDialog` extends QDialog
  - Methods: `__init__()`, `_setup_ui()`, `_on_view_clicked()`

**Key imports:** `__future__`, `PySide6.QtCore`, `PySide6.QtWidgets`, `services.translation_service`

---

#### `preferences_dialog.py` (309 LOC)

**Purpose:** 1 class

**Classes:**
- `PreferencesDialog` extends QDialog
  - Methods: `__init__()`, `_setup_ui()`, `_load_initial_preferences()`, `_on_accept()`, `_connect_signals()` (+1 more)

**Exception Handling:**
- 1 exception handling constructs

**Key imports:** `__future__`, `pathlib`, `PySide6.QtCore`, `PySide6.QtWidgets`, `services.preferences`
 (+1 more)

---

#### `return_dialog.py` (101 LOC)

**Purpose:** 1 class

**Classes:**
- `ReturnLoanDialog` extends QDialog
  - Methods: `__init__()`, `_load_open_loans()`, `get_selected_loan_id()`

**Key imports:** `__future__`, `PySide6.QtWidgets`, `sqlalchemy`, `sqlalchemy.orm`, `persistence.database`
 (+2 more)

---

### 📁 `libapp\views\mixins/`

#### `context_menu.py` (19 LOC)

**Purpose:** 1 class

**Classes:**
- `ContextMenuMixin` extends QWidget
  - Methods: `_popup_context()`

**Key imports:** `__future__`, `collections.abc`, `PySide6.QtWidgets`, `services.translation_service`

---

### 📁 `tests/`

#### `conftest.py` (30 LOC)

**Purpose:** 1 func

**Functions:**
- `isolated_db(tmp_path, monkeypatch)`

**Constants:**
- `ROOT` = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

**Key imports:** `os`, `sys`, `uuid`, `pytest`

---

#### `test_export_service.py` (38 LOC)

**Purpose:** 2 funcs

**Functions:**
- `test_export_metadata_generation()`
- `test_export_csv_basic(tmp_path)`

**Key imports:** `libapp.services.export_service`

---

#### `test_import_cleaning.py` (8 LOC)

**Purpose:** 1 func

**Functions:**
- `test_clean_authors()`

**Key imports:** `libapp.services.import_service`

---

#### `test_import_smoke.py` (87 LOC)

**Purpose:** 1 func

**Functions:**
- `test_import_without_isbn(tmp_path, monkeypatch)`

**Key imports:** `sys`, `pandas`, `libapp.persistence.database`, `libapp.persistence.models_sa`, `libapp.services.import_service`

---

#### `test_loans_rules.py` (64 LOC)

**Purpose:** 1 func

**Functions:**
- `test_no_double_open_loan(tmp_path, monkeypatch)`

**Key imports:** `__future__`, `sys`, `pytest`, `sqlalchemy`, `libapp.persistence.database`
 (+2 more)

---

#### `test_loans_smoke.py` (67 LOC)

**Purpose:** 1 func

**Functions:**
- `test_loan_and_return_flow(tmp_path, monkeypatch)`

**Key imports:** `__future__`, `sys`, `sqlalchemy`, `libapp.persistence.database`, `libapp.persistence.models_sa`
 (+1 more)

---

#### `test_smoke.py` (3 LOC)

**Purpose:** 1 func

**Functions:**
- `test_smoke()`

---

## 🔗 Internal Dependencies Graph

**File relationships** (who imports whom):

```
alembic\env.py
  └─> libapp\persistence\database.py
libapp\persistence\database.py
  └─> libapp\utils\paths.py
libapp\persistence\migrate.py
  └─> libapp\persistence\database.py
libapp\services\config_service.py
  └─> libapp\utils\paths.py
libapp\services\search_index.py
  └─> libapp\persistence\database.py
  └─> libapp\persistence\models_sa.py
run.py
  └─> libapp\app.py
tests\test_export_service.py
  └─> libapp\services\export_service.py
tests\test_import_cleaning.py
  └─> libapp\services\import_service.py
tests\test_import_smoke.py
  └─> libapp\persistence\database.py
  └─> libapp\persistence\models_sa.py
  └─> libapp\services\import_service.py
tests\test_loans_rules.py
  └─> libapp\persistence\database.py
  └─> libapp\persistence\models_sa.py
  └─> libapp\services\loan_service.py
tests\test_loans_smoke.py
  └─> libapp\persistence\database.py
  └─> libapp\persistence\models_sa.py
  └─> libapp\services\loan_service.py
```

## 📦 External Dependencies

**Third-party packages** (by usage):

- `__future__` — used in 49 files
- `PySide6` — used in 23 files
- `services` — used in 22 files
- `services.translation_service` — used in 21 files
- `PySide6.QtWidgets` — used in 21 files
- `sqlalchemy` — used in 20 files
- `persistence.models_sa` — used in 16 files
- `PySide6.QtCore` — used in 16 files
- `persistence` — used in 16 files
- `persistence.database` — used in 14 files
- `libapp` — used in 11 files
- `utils` — used in 10 files
- `services.preferences` — used in 10 files
- `sqlalchemy.orm` — used in 8 files
- `libapp.persistence.database` — used in 6 files
- `services.loan_service` — used in 6 files
- `libapp.persistence.models_sa` — used in 5 files
- `utils.paths` — used in 4 files
- `requests` — used in 4 files
- `utils.icon_helper` — used in 3 files
- `PySide6.QtGui` — used in 3 files
- `services.audit_service` — used in 3 files
- `export_dialog` — used in 3 files
- `services.export_service` — used in 3 files
- `pandas` — used in 3 files
- `yaml` — used in 2 files
- `alembic` — used in 2 files
- `base` — used in 2 files
- `libapp.utils.paths` — used in 2 files
- `models_sa` — used in 2 files
- `persistence.unit_of_work` — used in 2 files
- `openpyxl` — used in 2 files
- `__version__` — used in 2 files
- `bnf_select_dialog` — used in 2 files
- `natural_sort_proxy` — used in 2 files
- `loan_dialogs` — used in 2 files
- `services.types` — used in 2 files
- `services.import_service` — used in 2 files
- `pytest` — used in 2 files
- `libapp.services.import_service` — used in 2 files
- `libapp.services.loan_service` — used in 2 files
- `libapp.app` — used in 1 file
- `qdarktheme` — used in 1 file
- `views.loan_dialog` — used in 1 file
- `views.member_list` — used in 1 file
- `views.import_members_dialog` — used in 1 file
- `views.member_editor` — used in 1 file
- `views.overdue_alert_dialog` — used in 1 file
- `views.preferences_dialog` — used in 1 file
- `views.import_dialog` — used in 1 file
- `views.dashboard` — used in 1 file
- `views.book_editor` — used in 1 file
- `views.about_dialog` — used in 1 file
- `views.book_list` — used in 1 file
- `views` — used in 1 file
- `services.enhanced_logging_config` — used in 1 file
- `views.loan_dialogs` — used in 1 file
- `views.loan_list` — used in 1 file
- `sqlalchemy.ext.hybrid` — used in 1 file
- `repositories` — used in 1 file
- `database` — used in 1 file
- `difflib` — used in 1 file
- `platform` — used in 1 file
- `metrics_service` — used in 1 file
- `openpyxl.styles` — used in 1 file
- `openlibrary_service` — used in 1 file
- `googlebooks_service` — used in 1 file
- `bnf_service` — used in 1 file
- `base64` — used in 1 file
- `sqlalchemy.exc` — used in 1 file
- `PySide6.QtSvg` — used in 1 file
- `icon_helper` — used in 1 file
- `services.bnf_adapter` — used in 1 file
- `book_editor` — used in 1 file
- `loan_dialog` — used in 1 file
- `services.meta_search_service` — used in 1 file
- `services.loan_policy` — used in 1 file
- `services.column_mapping` — used in 1 file
- `member_editor` — used in 1 file
- `libapp.services.export_service` — used in 1 file

**Standard Library** (36 unique modules used)

## 🎯 Key Files (ranked by complexity)

1. **`project_mapper_qwenCoder_rev.py`** (complexity: 132.8)
   - 3 classes, 26 functions, 2 constants, 28 exception handlers
2. **`libapp\services\meta_search_service.py`** (complexity: 91.4)
   - 12 classes, 3 constants, 7 exception handlers
3. **`libapp\services\import_service.py`** (complexity: 82.4)
   - 6 classes, 11 functions, 6 constants, 15 exception handlers
4. **`libapp\services\audit_service.py`** (complexity: 45.5)
   - 2 classes, 12 functions, 11 constants, 1 exception handlers
5. **`libapp\persistence\models_sa.py`** (complexity: 44.3)
   - 8 classes
6. **`libapp\views\book_list.py`** (complexity: 36.3)
   - 2 classes, 2 functions, 1 constants, 5 exception handlers
7. **`libapp\services\types.py`** (complexity: 26.5)
   - 5 classes
8. **`libapp\app.py`** (complexity: 24.1)
   - 1 classes, 1 functions, 2 exception handlers
9. **`libapp\services\bnf_service.py`** (complexity: 22.9)
   - 2 classes, 2 functions, 1 constants, 4 exception handlers
10. **`libapp\services\googlebooks_service.py`** (complexity: 22.5)
   - 3 classes, 1 constants, 4 exception handlers
11. **`libapp\views\member_list.py`** (complexity: 22.4)
   - 2 classes, 1 constants, 2 exception handlers
12. **`libapp\views\loan_list.py`** (complexity: 21.5)
   - 2 classes, 1 constants, 2 exception handlers
13. **`libapp\services\loan_service.py`** (complexity: 21.3)
   - 1 classes, 4 functions, 5 exception handlers
14. **`libapp\services\metrics_service.py`** (complexity: 20.5)
   - 7 functions, 3 exception handlers
15. **`libapp\views\dashboard.py`** (complexity: 19.0)
   - 2 classes, 1 functions, 2 exception handlers

---

## Usage Guide for AI Coding Agents

### For Initial Context
When starting a new task, always:
1. Read this entire map to understand project structure
2. Identify relevant files from the structure section
3. Check dependencies before modifying files
4. Consult database schema when working with data models

### For Specific Tasks
- **Adding features**: Check "Key Files" section for entry points
- **Refactoring**: Review "Internal Dependencies Graph" to understand impact
- **Debugging**: Look at file's class/function list to locate code
- **Database work**: Refer to "Database Schema" section

### Best Practices
- Always maintain this map's structure when adding files
- Update dependencies when creating new modules
- Keep database schema in sync with migrations
- Use this map to avoid circular dependencies

---

*Generated by Project Mapper v1.0 - Optimized for LLM context*
