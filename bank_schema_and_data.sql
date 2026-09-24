/*
======================================================================
BANK DATABASE CREATION SCRIPT (Microsoft SQL Server 2025 Compatible)
======================================================================
Description:
    1. Creates a database named [BankDB].
    2. Defines tables for Customers, Accounts, Loans, Cashflow, etc.
    3. Generates MOCK DATA for ~100 customers with realistic distributions.
       - Credit Scores (Normal Distribution approximation)
       - Loan Eligibility based on Credit Score
       - Payment History / Delinquency simulation
======================================================================
*/

USE [master];
GO

IF EXISTS (SELECT name FROM sys.databases WHERE name = N'BankDB')
BEGIN
    ALTER DATABASE [BankDB] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE [BankDB];
END
GO

CREATE DATABASE [BankDB];
GO

USE [BankDB];
GO

/* ==================================================================================
   1. SCHEMA DEFINITION
   ================================================================================== */

-- 1.1 Reference Tables
CREATE TABLE [dbo].[AccountTypes] (
    [AccountTypeID] INT IDENTITY(1,1) PRIMARY KEY,
    [TypeName]      NVARCHAR(50) NOT NULL UNIQUE, -- 'Checking', 'Savings', 'CD'
    [BaseInterestRate] DECIMAL(5, 4) DEFAULT 0.00
);

CREATE TABLE [dbo].[LoanTypes] (
    [LoanTypeID]    INT IDENTITY(1,1) PRIMARY KEY,
    [TypeName]      NVARCHAR(50) NOT NULL UNIQUE, -- 'Home', 'Car', 'Personal', 'Business'
    [BaseInterestRate] DECIMAL(5, 4) DEFAULT 0.05
);

-- 1.2 Core Tables
CREATE TABLE [dbo].[Customers] (
    [CustomerID]    INT IDENTITY(1,1) PRIMARY KEY,
    [FirstName]     NVARCHAR(100) NOT NULL,
    [LastName]      NVARCHAR(100) NOT NULL,
    [DateOfBirth]   DATE NOT NULL,
    [SSN]           NVARCHAR(11) NOT NULL UNIQUE, -- Format XXX-XX-XXXX
    [Address]       NVARCHAR(200),
    [City]          NVARCHAR(100),
    [State]         NVARCHAR(2),
    [ZipCode]       NVARCHAR(10),
    [CreditScore]   INT CHECK (CreditScore BETWEEN 300 AND 850),
    [CreatedDate]   DATETIME2 DEFAULT GETDATE()
);

CREATE TABLE [dbo].[Accounts] (
    [AccountID]     INT IDENTITY(1,1) PRIMARY KEY,
    [CustomerID]    INT NOT NULL CONSTRAINT FK_Accounts_Customers FOREIGN KEY REFERENCES [dbo].[Customers]([CustomerID]),
    [AccountTypeID] INT NOT NULL CONSTRAINT FK_Accounts_AccountTypes FOREIGN KEY REFERENCES [dbo].[AccountTypes]([AccountTypeID]),
    [Balance]       DECIMAL(18, 2) DEFAULT 0.00,
    [InterestRate]  DECIMAL(5, 4) NOT NULL,
    [OpenDate]      DATE NOT NULL DEFAULT GETDATE(),
    [Status]        NVARCHAR(20) DEFAULT 'Active' -- 'Active', 'Closed', 'Frozen'
);

-- Indexes for Accounts
CREATE INDEX [IX_Accounts_CustomerID] ON [dbo].[Accounts]([CustomerID]);

CREATE TABLE [dbo].[Loans] (
    [LoanID]            INT IDENTITY(1,1) PRIMARY KEY,
    [CustomerID]        INT NOT NULL CONSTRAINT FK_Loans_Customers FOREIGN KEY REFERENCES [dbo].[Customers]([CustomerID]),
    [LoanTypeID]        INT NOT NULL CONSTRAINT FK_Loans_LoanTypes FOREIGN KEY REFERENCES [dbo].[LoanTypes]([LoanTypeID]),
    [OriginalAmount]    DECIMAL(18, 2) NOT NULL,
    [CurrentBalance]    DECIMAL(18, 2) NOT NULL,
    [InterestRate]      DECIMAL(5, 4) NOT NULL,
    [StartDate]         DATE NOT NULL,
    [TermMonths]        INT NOT NULL,
    [MonthlyPayment]    DECIMAL(18, 2) NOT NULL,
    [Status]            NVARCHAR(20) DEFAULT 'Active' -- 'Active', 'Paid', 'Defaulted'
);

-- Indexes for Loans
CREATE INDEX [IX_Loans_CustomerID] ON [dbo].[Loans]([CustomerID]);

-- 1.3 Transactional / History Tables

-- Records every scheduled payment for a loan (Projected Cashflow)
CREATE TABLE [dbo].[LoanAmortizationSchedule] (
    [ScheduleID]    BIGINT IDENTITY(1,1) PRIMARY KEY,
    [LoanID]        INT NOT NULL CONSTRAINT FK_Amort_Loans FOREIGN KEY REFERENCES [dbo].[Loans]([LoanID]),
    [PaymentNumber] INT NOT NULL,
    [PaymentDate]   DATE NOT NULL,
    [TotalPayment]  DECIMAL(18, 2) NOT NULL,
    [PrincipalComponent] DECIMAL(18, 2) NOT NULL,
    [InterestComponent]  DECIMAL(18, 2) NOT NULL,
    [RemainingBalance]   DECIMAL(18, 2) NOT NULL
);

-- Records actual payments made by customers
CREATE TABLE [dbo].[LoanPayments] (
    [PaymentID]     BIGINT IDENTITY(1,1) PRIMARY KEY,
    [LoanID]        INT NOT NULL CONSTRAINT FK_Payments_Loans FOREIGN KEY REFERENCES [dbo].[Loans]([LoanID]),
    [PaymentDate]   DATE NOT NULL DEFAULT GETDATE(),
    [AmountPaid]    DECIMAL(18, 2) NOT NULL,
    [LateFee]       DECIMAL(18, 2) DEFAULT 0.00,
    [IsLate]        BIT DEFAULT 0
);

CREATE TABLE [dbo].[AccountTransactions] (
    [TransactionID] BIGINT IDENTITY(1,1) PRIMARY KEY,
    [AccountID]     INT NOT NULL CONSTRAINT FK_Trans_Accounts FOREIGN KEY REFERENCES [dbo].[Accounts]([AccountID]),
    [TransactionDate] DATETIME2 NOT NULL DEFAULT GETDATE(),
    [TransactionType] NVARCHAR(50) NOT NULL, -- 'Deposit', 'Withdrawal', 'Transfer', 'Interest'
    [Amount]        DECIMAL(18, 2) NOT NULL,
    [Description]   NVARCHAR(200)
);

GO

/* ==================================================================================
   1.4 EXTENDED PROPERTIES (Documentation)
   ================================================================================== */
   
-- AccountTypes
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Reference table for types of accounts (Checking, Savings, CD)', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'AccountTypes';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Primary key for AccountTypes', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'AccountTypes', @level2type = N'COLUMN', @level2name = N'AccountTypeID';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Name of the account type', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'AccountTypes', @level2type = N'COLUMN', @level2name = N'TypeName';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Default interest rate for this account type', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'AccountTypes', @level2type = N'COLUMN', @level2name = N'BaseInterestRate';

-- LoanTypes
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Reference table for types of loans (Home, Car, Personal, Business)', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'LoanTypes';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Primary key for LoanTypes', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'LoanTypes', @level2type = N'COLUMN', @level2name = N'LoanTypeID';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Name of the loan type (Home, Car, Personal, Business)', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'LoanTypes', @level2type = N'COLUMN', @level2name = N'TypeName';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Base interest rate for this loan type', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'LoanTypes', @level2type = N'COLUMN', @level2name = N'BaseInterestRate';

-- Customers
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Stores customer personal and demographic information', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Customers';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Primary key for Customers', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Customers', @level2type = N'COLUMN', @level2name = N'CustomerID';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Customer First Name', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Customers', @level2type = N'COLUMN', @level2name = N'FirstName';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Customer Last Name', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Customers', @level2type = N'COLUMN', @level2name = N'LastName';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Date of Birth', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Customers', @level2type = N'COLUMN', @level2name = N'DateOfBirth';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Social Security Number (Unique)', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Customers', @level2type = N'COLUMN', @level2name = N'SSN';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Residential Address', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Customers', @level2type = N'COLUMN', @level2name = N'Address';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'City', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Customers', @level2type = N'COLUMN', @level2name = N'City';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'State Code (2 chars)', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Customers', @level2type = N'COLUMN', @level2name = N'State';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Zip / Postal Code', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Customers', @level2type = N'COLUMN', @level2name = N'ZipCode';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Credit Score (300-850)', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Customers', @level2type = N'COLUMN', @level2name = N'CreditScore';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Record creation timestamp', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Customers', @level2type = N'COLUMN', @level2name = N'CreatedDate';

-- Accounts
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Stores customer deposit accounts (Checking, Savings, etc.)', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Accounts';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Primary key for Accounts', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Accounts', @level2type = N'COLUMN', @level2name = N'AccountID';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Foreign key to Customers table', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Accounts', @level2type = N'COLUMN', @level2name = N'CustomerID';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Foreign key to AccountTypes table', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Accounts', @level2type = N'COLUMN', @level2name = N'AccountTypeID';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Current balance of the account', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Accounts', @level2type = N'COLUMN', @level2name = N'Balance';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Specific interest rate applied to this account', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Accounts', @level2type = N'COLUMN', @level2name = N'InterestRate';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Date the account was opened', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Accounts', @level2type = N'COLUMN', @level2name = N'OpenDate';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Account status (Active, Closed, Frozen)', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Accounts', @level2type = N'COLUMN', @level2name = N'Status';

-- Loans
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Stores customer loan accounts', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Loans';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Primary key for Loans', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Loans', @level2type = N'COLUMN', @level2name = N'LoanID';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Foreign key to Customers table', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Loans', @level2type = N'COLUMN', @level2name = N'CustomerID';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Foreign key to LoanTypes table', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Loans', @level2type = N'COLUMN', @level2name = N'LoanTypeID';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Initial principal amount of the loan', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Loans', @level2type = N'COLUMN', @level2name = N'OriginalAmount';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Outstanding principal balance', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Loans', @level2type = N'COLUMN', @level2name = N'CurrentBalance';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Annual interest rate', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Loans', @level2type = N'COLUMN', @level2name = N'InterestRate';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Date the loan started', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Loans', @level2type = N'COLUMN', @level2name = N'StartDate';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Loan term in months', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Loans', @level2type = N'COLUMN', @level2name = N'TermMonths';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Fixed monthly payment amount', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Loans', @level2type = N'COLUMN', @level2name = N'MonthlyPayment';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Loan status (Active, Paid, Defaulted)', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'Loans', @level2type = N'COLUMN', @level2name = N'Status';

-- LoanAmortizationSchedule
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Projected payment schedule for loans', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'LoanAmortizationSchedule';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Primary key for Schedule', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'LoanAmortizationSchedule', @level2type = N'COLUMN', @level2name = N'ScheduleID';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Foreign key to Loans table', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'LoanAmortizationSchedule', @level2type = N'COLUMN', @level2name = N'LoanID';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Sequential payment number (1 to Term)', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'LoanAmortizationSchedule', @level2type = N'COLUMN', @level2name = N'PaymentNumber';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Scheduled payment date', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'LoanAmortizationSchedule', @level2type = N'COLUMN', @level2name = N'PaymentDate';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Total value of the payment (Principal + Interest)', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'LoanAmortizationSchedule', @level2type = N'COLUMN', @level2name = N'TotalPayment';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Portion of payment applied to principal', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'LoanAmortizationSchedule', @level2type = N'COLUMN', @level2name = N'PrincipalComponent';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Portion of payment applied to interest', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'LoanAmortizationSchedule', @level2type = N'COLUMN', @level2name = N'InterestComponent';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Expected remaining balance after this payment', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'LoanAmortizationSchedule', @level2type = N'COLUMN', @level2name = N'RemainingBalance';

-- LoanPayments
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Actual payments received from customers', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'LoanPayments';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Primary key for LoanPayments', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'LoanPayments', @level2type = N'COLUMN', @level2name = N'PaymentID';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Foreign key to Loans table', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'LoanPayments', @level2type = N'COLUMN', @level2name = N'LoanID';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Date payment was received', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'LoanPayments', @level2type = N'COLUMN', @level2name = N'PaymentDate';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Amount received', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'LoanPayments', @level2type = N'COLUMN', @level2name = N'AmountPaid';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Charged late fee (if any)', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'LoanPayments', @level2type = N'COLUMN', @level2name = N'LateFee';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Flag indicating if payment was late (1=Yes, 0=No)', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'LoanPayments', @level2type = N'COLUMN', @level2name = N'IsLate';

-- AccountTransactions
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Ledger of all transactions for account history', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'AccountTransactions';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Primary key for AccountTransactions', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'AccountTransactions', @level2type = N'COLUMN', @level2name = N'TransactionID';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Foreign key to Accounts table', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'AccountTransactions', @level2type = N'COLUMN', @level2name = N'AccountID';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Date of transaction', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'AccountTransactions', @level2type = N'COLUMN', @level2name = N'TransactionDate';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Type of transaction (Deposit, Withdrawal, Transfer, Interest)', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'AccountTransactions', @level2type = N'COLUMN', @level2name = N'TransactionType';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Transaction amount (positive or negative based on context, here stored as absolute value largely but effectively signed in logic)', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'AccountTransactions', @level2type = N'COLUMN', @level2name = N'Amount';
EXEC sp_addextendedproperty @name = N'MS_Description', @value = N'Description or memo for the transaction', @level0type = N'SCHEMA', @level0name = N'dbo', @level1type = N'TABLE', @level1name = N'AccountTransactions', @level2type = N'COLUMN', @level2name = N'Description';

GO

/* ==================================================================================
   2. DATA GENERATION PROCEDURES & SEEDING
   ================================================================================== */

-- 2.1 Seed Reference Data
INSERT INTO [dbo].[AccountTypes] ([TypeName], [BaseInterestRate]) VALUES 
('Checking', 0.0000),
('Savings',  0.0150), -- 1.5%
('CD',       0.0425); -- 4.25%

INSERT INTO [dbo].[LoanTypes] ([TypeName], [BaseInterestRate]) VALUES 
('Home',     0.0650), -- 6.5%
('Car',      0.0725), -- 7.25%
('Personal', 0.1100), -- 11%
('Business', 0.0850); -- 8.5%

GO

-- 2.2 Mock Data Generator Script
-- We will use a dedicated stored procedure to generate mass data or just a clean script block.
-- For this file, we will use a script block.

SET NOCOUNT ON;
DECLARE @TotalCustomers INT = 100;
DECLARE @i INT = 1;

-- Pre-declare variables for loop
DECLARE @FirstName NVARCHAR(100), @LastName NVARCHAR(100);
DECLARE @DOB DATE, @CreditScore INT;
DECLARE @StreetNum INT, @StreetName NVARCHAR(100);
DECLARE @CustID INT;
DECLARE @AcctID INT;
DECLARE @RunBal DECIMAL(18,2);
DECLARE @TxDate DATE;
DECLARE @TxAmount DECIMAL(18,2);
DECLARE @TxTypeChoice INT;

-- Helper Tables for Random Names
DECLARE @FirstNames TABLE (Name NVARCHAR(50));
INSERT INTO @FirstNames VALUES ('James'), ('John'), ('Robert'), ('Michael'), ('William'), ('David'), ('Richard'), ('Joseph'), ('Thomas'), ('Charles'), ('Mary'), ('Patricia'), ('Jennifer'), ('Linda'), ('Elizabeth'), ('Barbara'), ('Susan'), ('Jessica'), ('Sarah'), ('Karen');

DECLARE @LastNames TABLE (Name NVARCHAR(50));
INSERT INTO @LastNames VALUES ('Smith'), ('Johnson'), ('Williams'), ('Brown'), ('Jones'), ('Garcia'), ('Miller'), ('Davis'), ('Rodriguez'), ('Martinez'), ('Hernandez'), ('Lopez'), ('Gonzalez'), ('Wilson'), ('Anderson'), ('Thomas'), ('Taylor'), ('Moore'), ('Jackson'), ('Martin');

DECLARE @Streets TABLE (Name NVARCHAR(50));
INSERT INTO @Streets VALUES ('Main St'), ('Oak Ave'), ('Maple Dr'), ('Cedar Ln'), ('Washington Blvd'), ('Lake View'), ('Sunset Dr'), ('Pine St'), ('Elm St'), ('Park Ave');

PRINT 'Generating Customers...';

WHILE @i <= @TotalCustomers
BEGIN
    -- 1. Generate Random Customer Attributes
    SELECT TOP 1 @FirstName = Name FROM @FirstNames ORDER BY NEWID();
    SELECT TOP 1 @LastName = Name FROM @LastNames ORDER BY NEWID();
    
    -- DOB between 18 and 80 years ago
    SET @DOB = DATEADD(DAY, -1 * (6570 + ABS(CHECKSUM(NEWID())) % 22000), GETDATE());
    
    -- Credit Score: Bell Curve-ish approximation
    -- Sum of 3 random numbers to approximate normal distribution
    -- Range approx 300-850, Mean ~700
    SET @CreditScore = 550 + (ABS(CHECKSUM(NEWID())) % 100) + (ABS(CHECKSUM(NEWID())) % 100) + (ABS(CHECKSUM(NEWID())) % 100);
    IF @CreditScore > 850 SET @CreditScore = 850;
    
    SELECT TOP 1 @StreetName = Name FROM @Streets ORDER BY NEWID();
    SET @StreetNum = ABS(CHECKSUM(NEWID())) % 9999 + 1;

    INSERT INTO [dbo].[Customers] 
    ([FirstName], [LastName], [DateOfBirth], [SSN], [Address], [City], [State], [ZipCode], [CreditScore])
    VALUES
    (@FirstName, @LastName, @DOB, 
     RIGHT('000' + CAST(ABS(CHECKSUM(NEWID())) % 1000 AS NVARCHAR), 3) + '-' + RIGHT('00' + CAST(ABS(CHECKSUM(NEWID())) % 100 AS NVARCHAR), 2) + '-' + RIGHT('0000' + CAST(ABS(CHECKSUM(NEWID())) % 10000 AS NVARCHAR), 4),
     CAST(@StreetNum AS NVARCHAR) + ' ' + @StreetName,
     'Metro City', 'NY', '10001', 
     @CreditScore
    );
    
    SET @CustID = SCOPE_IDENTITY();

    -- 2. Generate Accounts (90% chance Checking, 60% Savings, 20% CD)
    
    -- Checking
    IF (ABS(CHECKSUM(NEWID())) % 100) < 90
    BEGIN
        -- Start 1-24 months ago
        SET @TxDate = DATEADD(MONTH, -1 * (ABS(CHECKSUM(NEWID())) % 24 + 1), GETDATE());
        
        INSERT INTO [dbo].[Accounts] ([CustomerID], [AccountTypeID], [Balance], [InterestRate], [OpenDate], [Status])
        VALUES (@CustID, 1, 0, 0.00, @TxDate, 'Active');
        SET @AcctID = SCOPE_IDENTITY();

        -- Initial Deposit
        SET @RunBal = 500 + (ABS(CHECKSUM(NEWID())) % 2000);
        INSERT INTO [dbo].[AccountTransactions] ([AccountID], [TransactionDate], [TransactionType], [Amount], [Description])
        VALUES (@AcctID, @TxDate, 'Deposit', @RunBal, 'Initial Deposit');

        -- Simulating activity until today
        WHILE @TxDate < DATEADD(DAY, -1, GETDATE())
        BEGIN
            -- Advance time 2-7 days
            SET @TxDate = DATEADD(DAY, 2 + (ABS(CHECKSUM(NEWID())) % 6), @TxDate);
            IF @TxDate >= GETDATE() BREAK;

            SET @TxTypeChoice = ABS(CHECKSUM(NEWID())) % 100;
            
            -- 1. Income (Direct Deposit) - Occasional (e.g., twice a month approx 10% chance per random stride)
            IF @TxTypeChoice < 15
            BEGIN
                SET @TxAmount = 1500 + (ABS(CHECKSUM(NEWID())) % 1000);
                SET @RunBal = @RunBal + @TxAmount;
                INSERT INTO [dbo].[AccountTransactions] ([AccountID], [TransactionDate], [TransactionType], [Amount], [Description])
                VALUES (@AcctID, @TxDate, 'Deposit', @TxAmount, 'Direct Deposit');
            END
            -- 2. External Transfer In
            ELSE IF @TxTypeChoice < 20
            BEGIN
                SET @TxAmount = 100 + (ABS(CHECKSUM(NEWID())) % 500);
                SET @RunBal = @RunBal + @TxAmount;
                INSERT INTO [dbo].[AccountTransactions] ([AccountID], [TransactionDate], [TransactionType], [Amount], [Description])
                VALUES (@AcctID, @TxDate, 'Transfer', @TxAmount, 'Transfer from External Acct');
            END
            -- 3. Branch Deposit
            ELSE IF @TxTypeChoice < 25
            BEGIN
                SET @TxAmount = 50 + (ABS(CHECKSUM(NEWID())) % 200);
                SET @RunBal = @RunBal + @TxAmount;
                INSERT INTO [dbo].[AccountTransactions] ([AccountID], [TransactionDate], [TransactionType], [Amount], [Description])
                VALUES (@AcctID, @TxDate, 'Deposit', @TxAmount, 'Branch Deposit');
            END
            -- 4. Expenses (ATM, Check, Debit)
            ELSE
            BEGIN
                SET @TxAmount = -1 * (10 + (ABS(CHECKSUM(NEWID())) % 150));
                -- Only spend if we have money (prevent negative balance for simplicity, or allow small overdraft)
                IF (@RunBal + @TxAmount) > 0
                BEGIN
                    SET @RunBal = @RunBal + @TxAmount;
                    DECLARE @Desc NVARCHAR(50) = CASE 
                        WHEN @TxTypeChoice < 60 THEN 'Debit Purchase'
                        WHEN @TxTypeChoice < 80 THEN 'ATM Withdrawal'
                        ELSE 'Check Payment' END;

                    INSERT INTO [dbo].[AccountTransactions] ([AccountID], [TransactionDate], [TransactionType], [Amount], [Description])
                    VALUES (@AcctID, @TxDate, 'Withdrawal', @TxAmount, @Desc);
                END
            END
        END
        
        -- Update Final Balance
        UPDATE [dbo].[Accounts] SET Balance = @RunBal WHERE AccountID = @AcctID;
    END
    
    -- Savings
    IF (ABS(CHECKSUM(NEWID())) % 100) < 60
    BEGIN
        -- Start 1-36 months ago
        SET @TxDate = DATEADD(MONTH, -1 * (ABS(CHECKSUM(NEWID())) % 36 + 1), GETDATE());
        
        INSERT INTO [dbo].[Accounts] ([CustomerID], [AccountTypeID], [Balance], [InterestRate], [OpenDate], [Status])
        VALUES (@CustID, 2, 0, 0.015, @TxDate, 'Active');
        SET @AcctID = SCOPE_IDENTITY();

        -- Initial Deposit
        SET @RunBal = 1000 + (ABS(CHECKSUM(NEWID())) % 5000);
        INSERT INTO [dbo].[AccountTransactions] ([AccountID], [TransactionDate], [TransactionType], [Amount], [Description])
        VALUES (@AcctID, @TxDate, 'Deposit', @RunBal, 'Initial Deposit');

        -- Monthly Interest Loop
        WHILE @TxDate < DATEADD(MONTH, -1, GETDATE())
        BEGIN
            SET @TxDate = DATEADD(MONTH, 1, @TxDate);
            
            -- Interest
            SET @TxAmount = @RunBal * (0.015 / 12.0); -- Simple interest for mock
            SET @RunBal = @RunBal + @TxAmount;
            
            INSERT INTO [dbo].[AccountTransactions] ([AccountID], [TransactionDate], [TransactionType], [Amount], [Description])
            VALUES (@AcctID, @TxDate, 'Interest', @TxAmount, 'Monthly Interest');
            
            -- Occasional Deposit
            IF (ABS(CHECKSUM(NEWID())) % 100) < 20
            BEGIN
                SET @TxAmount = 100 + (ABS(CHECKSUM(NEWID())) % 500);
                SET @RunBal = @RunBal + @TxAmount;
                INSERT INTO [dbo].[AccountTransactions] ([AccountID], [TransactionDate], [TransactionType], [Amount], [Description])
                VALUES (@AcctID, @TxDate, 'Deposit', @TxAmount, 'Savings Deposit');
            END
        END
        
        UPDATE [dbo].[Accounts] SET Balance = @RunBal WHERE AccountID = @AcctID;
    END
    
    -- CD (Fixed)
    IF (ABS(CHECKSUM(NEWID())) % 100) < 20
    BEGIN
         -- Start 6-24 months ago
        SET @TxDate = DATEADD(MONTH, -1 * (ABS(CHECKSUM(NEWID())) % 24 + 1), GETDATE());

        INSERT INTO [dbo].[Accounts] ([CustomerID], [AccountTypeID], [Balance], [InterestRate], [OpenDate], [Status])
        VALUES (@CustID, 3, 0, 0.0425, @TxDate, 'Active');
        SET @AcctID = SCOPE_IDENTITY();

        -- Initial Deposit
        SET @RunBal = 5000 + (ABS(CHECKSUM(NEWID())) % 15000);
        INSERT INTO [dbo].[AccountTransactions] ([AccountID], [TransactionDate], [TransactionType], [Amount], [Description])
        VALUES (@AcctID, @TxDate, 'Deposit', @RunBal, 'Initial CD Deposit');

        -- Monthly Interest
        WHILE @TxDate < DATEADD(MONTH, -1, GETDATE())
        BEGIN
            SET @TxDate = DATEADD(MONTH, 1, @TxDate);
            SET @TxAmount = @RunBal * (0.0425 / 12.0);
            SET @RunBal = @RunBal + @TxAmount;
            
            INSERT INTO [dbo].[AccountTransactions] ([AccountID], [TransactionDate], [TransactionType], [Amount], [Description])
            VALUES (@AcctID, @TxDate, 'Interest', @TxAmount, 'CD Interest');
        END

        UPDATE [dbo].[Accounts] SET Balance = @RunBal WHERE AccountID = @AcctID;
    END

    -- 3. Generate Loans (Based on Credit Score)
    -- Higher score = Higher chance of loan & verification
    DECLARE @LoanChance INT = 30;
    IF @CreditScore > 700 SET @LoanChance = 60;
    IF @CreditScore > 750 SET @LoanChance = 80;

    IF (ABS(CHECKSUM(NEWID())) % 100) < @LoanChance
    BEGIN
        DECLARE @LoanTypeID INT;
        DECLARE @Principal DECIMAL(18,2);
        DECLARE @Rate DECIMAL(5,4);
        DECLARE @Term INT;
        
        -- Pick Loan Type
        -- 1:Home(30%), 2:Car(40%), 3:Personal(20%), 4:Biz(10%)
        DECLARE @Roll INT = ABS(CHECKSUM(NEWID())) % 100;
        IF @Roll < 30      
        BEGIN 
            SET @LoanTypeID = 1; -- Home
            SET @Principal = 150000 + (ABS(CHECKSUM(NEWID())) % 350000); 
            SET @Term = 360; 
            SET @Rate = 0.065; 
        END
        ELSE IF @Roll < 70 
        BEGIN 
            SET @LoanTypeID = 2; -- Car
            SET @Principal = 15000 + (ABS(CHECKSUM(NEWID())) % 40000); 
            SET @Term = 60; 
            SET @Rate = 0.0725; 
        END
        ELSE IF @Roll < 90 
        BEGIN 
            SET @LoanTypeID = 3; -- Personal
            SET @Principal = 2000 + (ABS(CHECKSUM(NEWID())) % 20000); 
            SET @Term = 24; 
            SET @Rate = 0.11; 
        END
        ELSE               
        BEGIN 
            SET @LoanTypeID = 4; -- Biz
            SET @Principal = 50000 + (ABS(CHECKSUM(NEWID())) % 100000); 
            SET @Term = 120; 
            SET @Rate = 0.085; 
        END

        -- Adjust Rate by Credit Score (Lower score = Higher Rate)
        IF @CreditScore < 650 SET @Rate = @Rate + 0.02;
        ELSE IF @CreditScore < 720 SET @Rate = @Rate + 0.005;
        ELSE IF @CreditScore > 780 SET @Rate = @Rate - 0.0025; -- Discount

        -- Calculate PMT (Monthly Payment)
        -- Formula: M = P [ i(1+i)^n ] / [ (1+i)^n – 1 ]
        DECLARE @MonthlyRate FLOAT = @Rate / 12.0;
        DECLARE @MonthlyPayment DECIMAL(18,2);
        
        IF @MonthlyRate = 0 
            SET @MonthlyPayment = @Principal / @Term;
        ELSE
            SET @MonthlyPayment = @Principal * (@MonthlyRate * POWER(1 + @MonthlyRate, @Term)) / (POWER(1 + @MonthlyRate, @Term) - 1);

        -- Start date 1-3 years ago to simulate active loans
        DECLARE @LoanStartDate DATE = DATEADD(MONTH, -1 * (ABS(CHECKSUM(NEWID())) % 36 + 1), GETDATE());

        INSERT INTO [dbo].[Loans] 
        ([CustomerID], [LoanTypeID], [OriginalAmount], [CurrentBalance], [InterestRate], [StartDate], [TermMonths], [MonthlyPayment], [Status])
        VALUES
        (@CustID, @LoanTypeID, @Principal, @Principal, @Rate, @LoanStartDate, @Term, @MonthlyPayment, 'Active');

        DECLARE @LoanID INT = SCOPE_IDENTITY();

        -- 3.1 Generate Amortization Schedule (Projected)
        DECLARE @p INT = 1;
        DECLARE @RemBal DECIMAL(18,2) = @Principal;
        DECLARE @PayDate DATE = @LoanStartDate;
        
        -- Simple iteration for schedule
        WHILE @p <= @Term
        BEGIN
            SET @PayDate = DATEADD(MONTH, 1, @PayDate);
            DECLARE @InterestPart DECIMAL(18,2) = @RemBal * @MonthlyRate;
            DECLARE @PrincipalPart DECIMAL(18,2) = @MonthlyPayment - @InterestPart;
            
            IF @RemBal < @PrincipalPart
            BEGIN
                SET @PrincipalPart = @RemBal;
                SET @MonthlyPayment = @PrincipalPart + @InterestPart;
                SET @RemBal = 0;
            END
            ELSE
            BEGIN
                SET @RemBal = @RemBal - @PrincipalPart;
            END

            INSERT INTO [dbo].[LoanAmortizationSchedule]
            ([LoanID], [PaymentNumber], [PaymentDate], [TotalPayment], [PrincipalComponent], [InterestComponent], [RemainingBalance])
            VALUES
            (@LoanID, @p, @PayDate, @MonthlyPayment, @PrincipalPart, @InterestPart, @RemBal);

            IF @RemBal <= 0 BREAK;
            SET @p = @p + 1;
        END

        -- 3.2 Backfill "Actual" Payments (Simulate history)
        -- Check how many months have passed since StartDate
        DECLARE @MonthsPassed INT = DATEDIFF(MONTH, @LoanStartDate, GETDATE());
        
        -- Cap history at Term length (prevent error if loan is older than term)
        IF @MonthsPassed > @Term SET @MonthsPassed = @Term;

        DECLARE @m INT = 1;
        
        WHILE @m <= @MonthsPassed
        BEGIN
            -- Get the EXACT scheduled amount for this month
            DECLARE @ScheduledAmount DECIMAL(18,2);
            SELECT @ScheduledAmount = TotalPayment 
            FROM [dbo].[LoanAmortizationSchedule] 
            WHERE LoanID = @LoanID AND PaymentNumber = @m;

            -- Determine if customer paid on time or late (Based on Credit Score)
            DECLARE @PaymentStatus INT = ABS(CHECKSUM(NEWID())) % 100;
            DECLARE @IsLate BIT = 0;
            DECLARE @PaidAmount DECIMAL(18,2) = @ScheduledAmount;

            -- Thresholds
            -- Removed "Missed" (skip row) logic to ensure continuity as requested
            DECLARE @LateProb INT = 5; -- 5% chance to be late
            
            IF @CreditScore < 600 SET @LateProb = 20;
            
            IF @PaymentStatus < @LateProb
            BEGIN
                -- Late Payment
                SET @IsLate = 1;
            END

            INSERT INTO [dbo].[LoanPayments] ([LoanID], [PaymentDate], [AmountPaid], [IsLate])
            VALUES (@LoanID, DATEADD(MONTH, @m, @LoanStartDate), @PaidAmount, @IsLate);
            
            -- Update Current Balance on Loan Table
            DECLARE @PrinPaid DECIMAL(18,2) = (SELECT PrincipalComponent FROM [dbo].[LoanAmortizationSchedule] WHERE LoanID = @LoanID AND PaymentNumber = @m);
            
            UPDATE [dbo].[Loans] 
            SET CurrentBalance = CurrentBalance - @PrinPaid
            WHERE LoanID = @LoanID;

            SET @m = @m + 1;
        END
    END
    
    SET @i = @i + 1;
END

PRINT 'Database setup and mock data generation complete.';
GO
