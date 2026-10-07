SELECT date(created_at) AS day,
  COUNT(*) FILTER (WHERE name = 'ghost_text_kept') * 1.0
  / COUNT(*) FILTER (WHERE name = 'ghost_text_shown')
    AS keep_rate
FROM events
WHERE name IN ('ghost_text_shown', 'ghost_text_kept')
  AND created_at > now() - interval '30 days'
GROUP BY day
ORDER BY day;
