"""
SEO2 — Chi?n l??c SEO toàn di?n cho topdev.vn

80% Content & Backlink | 20% Automation
"""
import sys

def show_strategy():
    """Hi?n th? chi?n l??c t?ng th?."""
    from content.planner import print_plan, get_plan_summary
    from content.keyword_research import print_keyword_report
    from backlinks.tracker import print_backlink_plan

    print("=" * 65)
    print("  SEO2 - CHIEN LUOC TOAN DIEN CHO TOPDEV.VN")
    print("  80% Content & Backlink | 20% Automation")
    print("=" * 65)

    # Content Strategy
    print_plan()
    print()

    # Keyword Research
    try:
        print_keyword_report()
    except Exception as e:
        print(f"Keyword report error: {e}")
    print()

    # Backlink Strategy
    try:
        print_backlink_plan()
    except Exception as e:
        print(f"Backlink plan error: {e}")
    print()

    # Automation notice
    print("-" * 65)
    print("  AUTOMATION (20%) - Chay khi can")
    print("  " + "=" * 61)
    print("  python main.py --search    Gioi han 25 session/ngay, mobile 70%")
    print("  python main.py --direct    Truy cap truc tiep (khong qua Google)")
    print("  python main.py --plan      Xem content plan 30 ngay")
    print("  python main.py --keywords  Xem keyword research")
    print("  python main.py --backlinks Xem backlink strategy")
    print("-" * 65)


if __name__ == "__main__":
    if "--auto" in sys.argv or "--search" in sys.argv:
        # 20% Automation — gi?i h?n 25 session/ngày
        from utils.rate_limiter import can_run_session, mark_session_run, get_today_summary
        import asyncio

        summary = get_today_summary()
        print(f"[RateLimit] H�m nay ch?y: {summary['ran']}/{summary['ran'] + summary['remaining']} session")

        allowed, reason = can_run_session()
        if not allowed:
            print(f"[RateLimit] {reason}")
            sys.exit(1)

        # M?c d?nh dùng search flow (traffic t? Google) — t? nhi�n h?n direct
        use_search = "--search" in sys.argv or not "--direct" in sys.argv
        mode = "SEARCH (Google)" if use_search else "DIRECT"
        print(f"Ch?y automation mode — Traffic: {mode} (gi?i h?n 25 session/ngày)")

        from core.browser_manager import BrowserManager

        async def run_limited():
            mgr = BrowserManager()
            browser = await mgr.launch_browser()
            page = await mgr.create_context(browser)

            if use_search:
                from tests.test_search_flow import run_search_flow
                await run_search_flow(page)
            else:
                from tests.test_direct_access import run_deep_session
                await run_deep_session(page)

            await mgr.close()

        asyncio.run(run_limited())
        mark_session_run()
        print(f"[RateLimit] D? xong. Còn {get_today_summary()['remaining']} session h�m nay.")

    elif "--plan" in sys.argv:
        from content.planner import print_plan
        print_plan()

    elif "--keywords" in sys.argv:
        from content.keyword_research import print_keyword_report
        print_keyword_report()

    elif "--backlinks" in sys.argv:
        from backlinks.tracker import print_backlink_plan
        print_backlink_plan()

    else:
        show_strategy()
