DECLARE
    table_count NUMBER;
BEGIN
    SELECT COUNT(*) INTO table_count FROM user_tables WHERE table_name = 'OPENINFRA_DOCUMENT_STATE';
    IF table_count = 0 THEN
        EXECUTE IMMEDIATE '
            CREATE TABLE openinfra_document_state (
                state_key VARCHAR2(64) PRIMARY KEY,
                payload CLOB NOT NULL,
                version NUMBER(20) DEFAULT 0 NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
                CONSTRAINT ck_openinfra_state_payload CHECK (payload IS JSON)
            )';
    END IF;
END;
/

DECLARE
    state_count NUMBER;
BEGIN
    SELECT COUNT(*) INTO state_count FROM openinfra_document_state WHERE state_key = 'global';
    IF state_count = 0 THEN
        INSERT INTO openinfra_document_state (state_key, payload, version)
        VALUES ('global', '{}', 0);
    END IF;
END;
/
