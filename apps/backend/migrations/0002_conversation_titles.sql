-- Phase 7: Add conversation title and title_source columns to conversations table

ALTER TABLE conversations ADD COLUMN title TEXT DEFAULT 'New Conversation';
ALTER TABLE conversations ADD COLUMN title_source TEXT DEFAULT 'auto' CHECK (title_source IN ('auto', 'user'));
