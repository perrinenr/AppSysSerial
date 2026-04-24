USE [master]
GO

IF OBJECT_ID('[dbo].[AppSysSerial]', 'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[AppSysSerial](
        [SN] [nvarchar](13) NOT NULL,
        [ValidityDays] [int] NULL,
        [ExpiryDate] [nvarchar](10) NULL,
        CONSTRAINT [PK_AppSysSerial] PRIMARY KEY CLUSTERED ([SN] ASC)
    ) ON [PRIMARY]
END
GO

-- Test serials. Run only if you want sample data.
IF NOT EXISTS (SELECT 1 FROM dbo.AppSysSerial WHERE SN = '1234567890123')
    INSERT INTO dbo.AppSysSerial (SN, ValidityDays, ExpiryDate)
    VALUES ('1234567890123', 30, NULL);

IF NOT EXISTS (SELECT 1 FROM dbo.AppSysSerial WHERE SN = '2222222222222')
    INSERT INTO dbo.AppSysSerial (SN, ValidityDays, ExpiryDate)
    VALUES ('2222222222222', 60, NULL);

IF NOT EXISTS (SELECT 1 FROM dbo.AppSysSerial WHERE SN = '9999999999999')
    INSERT INTO dbo.AppSysSerial (SN, ValidityDays, ExpiryDate)
    VALUES ('9999999999999', 30, '2026-05-20');
GO
