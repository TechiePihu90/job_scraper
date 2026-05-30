import asyncio
from app.db_client import db_client


async def main():
    await db_client.connect()
    rows = await db_client.fetch_all_jobs(page=1, limit=100)
    print('TOTAL', len(rows))
    from collections import Counter
    counts = Counter(j.source_ats for j in rows)
    print('ATS_COUNTS', dict(counts))
    for ats in sorted(counts):
        ats_rows = [j for j in rows if j.source_ats == ats]
        print('\nATS', ats, 'SAMPLE_COUNT', len(ats_rows), 'MAX_LEN', max((len(j.description) for j in ats_rows), default=0), 'MIN_LEN', min((len(j.description) for j in ats_rows), default=0))
        for j in ats_rows[:3]:
            print('  JOB', j.job_id, 'DESC_LEN', len(j.description), 'START', (j.description[:80]).replace('\n', ' '), 'END', j.description[-80:])
    await db_client.disconnect()


asyncio.run(main())
