# Documentation Structure

This directory contains all project documentation, organized into logical categories.

## 📁 Directory Structure

```
docs/
├── README.md                    # This file - documentation guide
├── research_log.md             # 📖 MASTER LOG - Complete project history
├── pipeline_architecture.md    # 🏗️  System architecture & design
├── bugs_to_fix.md             # 🐛 Active bug tracking
│
├── sessions/                   # 📊 Session summaries & work logs
│   ├── SESSION_18_CLEANUP_SUMMARY.md
│   ├── SESSION_19_EXECUTIVE_SUMMARY.md
│   ├── week2_work_summary.md
│   └── refactoring_summary_2025-12-05.md
│
├── analysis/                   # 📈 Technical analysis & findings
│   ├── CRITICAL_FIXES_SESSION_19.md
│   ├── WINDOW_SIZE_ANALYSIS_PRELIMINARY.md
│   ├── OPTIMAL_THRESHOLD_IMPLEMENTATION.md
│   ├── FINAL_COMPREHENSIVE_REPORT_2025-12-05.md
│   ├── BACKTEST_EXECUTION_FINDINGS_2025-12-05.md
│   └── SCRIPT_ANALYSIS.md
│
└── archive/                    # 📦 Historical/deprecated docs
    ├── debug_summary.md
    ├── v2_vs_v3_comparison.md
    ├── v14_vidyamurthy_implementation.md
    ├── kalman_analysis_summary.md
    ├── config_audit_etf_vs_stocks.md
    ├── cross_validation_findings.md
    └── cscv_vs_cpcv.md
```

---

## 🎯 Essential Documents

### 1. **research_log.md** - THE MASTER LOG
**Purpose**: Complete chronological history of the entire project
**Contents**:
- All sessions from inception to present
- Key decisions and rationale
- Implementation milestones
- Performance findings
- Lessons learned

**When to update**: After each significant session or milestone

### 2. **pipeline_architecture.md** - SYSTEM DESIGN
**Purpose**: Technical architecture documentation
**Contents**:
- System components and data flow
- Module responsibilities
- Configuration management
- Validation framework
- Integration points

**When to update**: After architectural changes or new features

### 3. **bugs_to_fix.md** - ACTIVE TRACKING
**Purpose**: Current issues and their status
**Contents**:
- Open bugs
- Priority levels
- Reproduction steps
- Fix status

**When to update**: As bugs are discovered or resolved

---

## 📊 Session Reports (`sessions/`)

Detailed summaries of work sessions, including:
- Session objectives
- Work completed
- Code changes
- Results and findings
- Next steps

**Latest Sessions**:
- **SESSION_19** (2025-12-07): Critical fixes + window size testing
- **SESSION_18** (2025-12-06): Code cleanup + comprehensive audit
- **Week 2 Summary**: Formation data fixes + new configs

---

## 📈 Analysis Reports (`analysis/`)

In-depth technical analyses and findings:

### Recent Reports
- **CRITICAL_FIXES_SESSION_19.md**: Cointegration monitoring + bug fixes
- **WINDOW_SIZE_ANALYSIS_PRELIMINARY.md**: Empirical window size testing (180-90 recommendation)
- **OPTIMAL_THRESHOLD_IMPLEMENTATION.md**: Vidyamurthy Ch.8 threshold optimization
- **FINAL_COMPREHENSIVE_REPORT_2025-12-05.md**: Week 2 comprehensive findings

### Key Findings
- Window sizes: 180-90 generates 167% more trades than 252-252
- Cointegration monitoring: Prevents 4-6 drift-based losses per test
- Optimal thresholds: Nonparametric method preferred over fixed 2.0σ

---

## 📦 Archive (`archive/`)

Historical documents kept for reference:
- Early implementation notes
- Deprecated analyses
- Version comparison studies
- Initial debug summaries

**Note**: These documents may contain outdated information. Refer to current docs for latest state.

---

## 📝 Document Naming Convention

**Session Reports**: `SESSION_XX_description.md` or `week_X_work_summary.md`
**Analysis**: `TOPIC_ANALYSIS_YYYY-MM-DD.md` or `TOPIC_IMPLEMENTATION.md`
**Archive**: Original names preserved

---

## 🔄 Maintenance Guidelines

### Adding New Documents

1. **Session Report** → `sessions/SESSION_XX_title.md`
2. **Analysis** → `analysis/TOPIC_description.md`
3. **Historical** → `archive/old_document.md`

### Updating Core Docs

**research_log.md**:
- Add new session entry at the end
- Update "Current Status" section
- Add to "Key Milestones" if significant

**pipeline_architecture.md**:
- Update relevant section (Data Flow, Components, etc.)
- Add version/date to changes
- Update diagrams if needed

**bugs_to_fix.md**:
- Mark completed bugs as ✅ FIXED
- Add new bugs with priority
- Archive resolved issues

---

## 📚 Quick Reference

**Want to know...**
- Project history? → `research_log.md`
- How system works? → `pipeline_architecture.md`
- Current issues? → `bugs_to_fix.md`
- Latest session? → `sessions/SESSION_19_EXECUTIVE_SUMMARY.md`
- Window size findings? → `analysis/WINDOW_SIZE_ANALYSIS_PRELIMINARY.md`
- Implementation details? → `analysis/CRITICAL_FIXES_SESSION_19.md`

---

## 🎓 Academic References

Key papers cited throughout documentation:
- **Vidyamurthy (2004)**: Pairs Trading - Quantitative Methods and Analysis
- **Gatev et al. (2006)**: Pairs Trading: Performance of a Relative-Value Arbitrage Rule
- **Gregory et al. (2011)**: Monitoring cointegration breakdowns
- **Bailey et al. (2016)**: PBO and overfitting detection
- **Chan (2013)**: Algorithmic Trading
- **Nath (2003)**: Cointegration instability

---

**Last Updated**: 2025-12-07 (Session 19)
**Maintained By**: Research Team
**Status**: ✅ ACTIVE - Regularly Updated
