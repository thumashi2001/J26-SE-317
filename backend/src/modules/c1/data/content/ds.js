import { S, M, D } from './helpers.js';
export default {
  semester: 'Y3S1',
  module_code: 'SE3060',
  module_name: 'Database Systems',
  topics: {
    object_relational_db: {
      label: 'Object-Relational Databases and PL/SQL',
      lectures: 'L01-L02b, Lab05',
      practice: [
        S(
          `Which problem of the pure relational model do object-relational databases help to solve?`,
          [`Set-valued attributes need extra tables and many joins`, `Tables cannot have primary or foreign keys`, `SQL cannot filter rows with a WHERE clause`, `Atomic attributes cannot store numbers`],
          0,
          `A set-valued attribute such as phone numbers or children must be split into more tables in 3NF, so queries need many joins. ORDB lets one attribute hold a set.`,
          'concept'
        ),
        S(
          `After you run CREATE TYPE BarType AS OBJECT (...) in Oracle, what has been created?`,
          [`An empty table named BarType`, `A table with one default row`, `A type definition only, no table`, `A view over the bars table`],
          2,
          `A type declaration does not create a table. You still need a statement like CREATE TABLE bars OF BarType to get row objects.`,
          'concept'
        ),
        S(
          `Table Sells has a column beer of type REF BeerType. Which query correctly reads the beer names?`,
          [`SELECT beer.name FROM Sells`, `SELECT s.beer.name FROM Sells s`, `SELECT Sells.beer.name FROM Sells`, `SELECT name(beer) FROM Sells s`],
          1,
          `You must use an alias for the table and then the dot operator, which dereferences the REF automatically. Using the table name or no alias does not work.`,
          'scenario'
        ),
        S(
          `How does a map method differ from an order method?`,
          [`A map method takes a second object and returns a negative, zero or positive number`, `An order method has no parameters and returns one scalar for each object`, `A map method must be called once for every pair of objects being compared`, `A map method returns a scalar for each object, an order method compares two objects`],
          3,
          `A map method maps an object to a scalar such as a number, then the scalars are compared. An order method takes another object of the same type and returns <0, 0 or >0.`,
          'compare'
        ),
        S(
          `Which of these can a subtype NOT do to the type it inherits from?`,
          [`Add a new attribute`, `Override a parent method`, `Drop an inherited attribute`, `Add a new method`],
          2,
          `A subtype can add attributes and methods and can override methods. It cannot drop or change the type of an attribute it inherits.`,
          'not'
        ),
        S(
          `What is the correct order of steps for using an explicit cursor in PL/SQL?`,
          [`DECLARE, OPEN, FETCH, CLOSE`, `OPEN, DECLARE, FETCH, CLOSE`, `DECLARE, FETCH, OPEN, CLOSE`, `DECLARE, OPEN, CLOSE, FETCH`],
          0,
          `You declare the cursor, open it, fetch rows one at a time, and close it before the block ends. Fetching after closing causes an error.`,
          'order'
        ),
        M(
          `Which statements about VARRAY and nested table types in Oracle are true?`,
          [`A VARRAY type needs a maximum size when it is declared`, `A nested table type is created with AS TABLE OF a type`, `Creating a VARRAY type allocates storage for all its elements`, `A table column of nested table type needs a STORE AS clause`],
          [0, 1, 3],
          `A VARRAY type is only a definition, so it allocates no space. A nested table column needs NESTED TABLE ... STORE AS to say where its rows are kept.`,
          'multi'
        ),
        M(
          `Which statements about nested table DML are true?`,
          [`Setting the nested column to NULL removes the whole nested table`, `proj_list() creates a nested table that has no rows`, `A TABLE expression is used to pick the nested table to change`, `NULL and an empty constructor mean exactly the same thing`],
          [0, 1, 2],
          `NULL and an empty collection are different: NULL has no nested table, while an empty constructor gives a table with zero rows.`,
          'multi'
        ),
        M(
          `Which statements about a PL/SQL block are true?`,
          [`The execution section starts with BEGIN and is mandatory`, `The declaration section is optional`, `The exception section is mandatory`, `Each statement ends with a semicolon`],
          [0, 1, 3],
          `Only the execution section is mandatory. The DECLARE and EXCEPTION sections are optional.`,
          'multi'
        ),
        M(
          `Which statements about subtypes in Oracle are true?`,
          [`A subtype is created with the UNDER keyword`, `A type must be NOT FINAL before it can have subtypes`, `Object types are final by default`, `Methods are final by default`],
          [0, 1, 2],
          `Types are final by default, but methods are not. A method is final only if you declare it FINAL.`,
          'multi'
        ),
      ],
      diagnostic: [
        D(
          `A SELECT returns many rows and your PL/SQL code must process them one row at a time. What do you need?`,
          [`A nested table type`, `A single SELECT INTO statement`, `A PL/SQL constant`, `An explicit cursor`],
          3,
          `SELECT INTO works for one row. An explicit cursor holds many rows and lets you process one current row at a time.`,
          'scenario'
        ),
        D(
          `You must sort and group a very large number of objects of one type. Which comparison method is more efficient?`,
          [`An order method, because it needs fewer calls`, `A map method, because it maps all objects to scalars first`, `An order method, because it compares pairs directly`, `Both cost the same, only the syntax is different`],
          1,
          `One map call turns all objects into scalars that are then sorted. An order method compares only two objects at a time, so it is called many times.`,
          'scenario'
        ),
        D(
          `person_tab holds Person_type, Student_type and PartTimeStudent_type rows. Which condition returns only Student_type rows, not part-time students?`,
          [`VALUE(s) IS OF (ONLY Student_type)`, `VALUE(s) IS OF (Student_type)`, `VALUE(s) IS OF (Person_type)`, `TREAT(VALUE(s) AS Student_type)`],
          0,
          `IS OF (Student_type) also returns its subtypes. The ONLY keyword limits the result to exactly that type.`,
          'concept'
        ),
      ],
    },

    file_organization_indexing: {
      label: 'File Organization and Indexing',
      lectures: 'L03',
      practice: [
        S(
          `Which pairing of file organization and strength is correct?`,
          [`Sorted file: best for equality selections only`, `Heap file: insert a record at the end of the file`, `Hashed file: best for range searches`, `Heap file: range search without a full scan`],
          1,
          `A heap file adds new records at the end, but searches must scan the file. Hashed files suit equality searches and sorted files suit range searches.`,
          'compare'
        ),
        S(
          `What is a record id (rid) made of?`,
          [`<key value, page id>`, `<file id, slot number>`, `<page id, slot number>`, `<bucket id, key value>`],
          2,
          `Records live in slots on pages, so the rid is the page id plus the slot number.`,
          'concept'
        ),
        S(
          `How many clustered indexes can one table have?`,
          [`One for each column`, `Two, one tree and one hash`, `As many as the DBA needs`, `At most one`],
          3,
          `Data records can be sorted in only one way, so a table can have at most one clustered index.`,
          'concept'
        ),
        S(
          `A B+ tree has average fanout 133. About how many records can a tree of height 3 hold?`,
          [`2,352,637`, `17,689`, `399`, `312,900,700`],
          0,
          `Capacity is fanout to the power of height: 133 x 133 x 133 = 2,352,637. The value 312,900,700 is for height 4.`,
          'calc'
        ),
        S(
          `When a B+ tree leaf node splits, what happens to the middle key?`,
          [`It is deleted to keep the leaf small`, `It moves into the right sibling only`, `It is copied up and also stays in a leaf`, `It is pushed up and removed from the leaf`],
          2,
          `Leaf splits copy the middle key up, so it still appears in a leaf. Index node splits push the middle key up, so it appears only once.`,
          'compare'
        ),
        S(
          `In extendible hashing, a bucket whose local depth equals the global depth overflows. What happens?`,
          [`An overflow page is chained to the full bucket`, `The directory doubles and only that bucket splits`, `All buckets are rehashed into twice as many pages`, `The hash function is replaced with a new one`],
          1,
          `Only the directory is doubled, which is cheap, and just the full bucket is split. Rehashing the whole file would be expensive.`,
          'scenario'
        ),
        M(
          `Which statements about indexes are true?`,
          [`An index can speed up selections on its search key`, `Indexes take space, so only useful ones should be created`, `An index may slow down some inserts, updates and deletes`, `A search key must always be the primary key`],
          [0, 1, 2],
          `A search key can be any subset of fields. It is not the same as a key that uniquely identifies records.`,
          'multi'
        ),
        M(
          `Which statements about hash-based indexes are true?`,
          [`They work best for equality selections`, `They cannot support range searches`, `Static hashing can build long overflow chains`, `Static hashing adds primary pages automatically as data grows`],
          [0, 1, 2],
          `Static hashing has a fixed number of primary pages. Extendible and linear hashing are the dynamic fixes.`,
          'multi'
        ),
        M(
          `Which statements about B+ trees are true?`,
          [`The tree is kept height-balanced`, `Every non-root node holds between d and 2d entries`, `It supports both equality and range searches`, `Every node must always be completely full`],
          [0, 1, 2],
          `The minimum occupancy is about 50 percent except for the root. Nodes do not have to be full.`,
          'multi'
        ),
        M(
          `Which statements about the alternatives for data entries in an index are true?`,
          [`In Alt. 1 the data entry is the data record itself`, `In Alt. 2 the data entry is a key and one rid`, `In Alt. 3 the data entry holds a key and only one rid`, `In Alt. 2 the data entry holds a key and a list of rids`],
          [0, 1],
          `Alt. 3 is the one that stores a key with a list of rids. Alt. 2 stores a key with a single rid.`,
          'multi'
        ),
      ],
      diagnostic: [
        D(
          `What is the difference between a search key and a key of a relation?`,
          [`A search key must be unique and minimal, a key can be any subset of fields`, `They are the same thing, only the names are different`, `A key is used only by hash indexes, a search key only by trees`, `A search key can be any subset of fields, a key must be unique and minimal`],
          3,
          `Any subset of fields can be a search key for an index. A key is a minimal set of fields that identifies a record uniquely.`,
          'compare'
        ),
        D(
          `After a delete, a B+ tree leaf has d-1 entries. What should be tried first?`,
          [`Redistribute entries by borrowing from a sibling`, `Merge the leaf with its sibling immediately`, `Split the leaf into two new leaves`, `Leave it, because only the root needs 50 percent fill`],
          0,
          `The leaf is below half-full, so first try to borrow from a sibling. If that fails, merge the two nodes.`,
          'scenario'
        ),
        D(
          `An index has search key <age, sal>. Which query is an equality query on this key?`,
          [`age = 20`, `age = 20 AND sal = 75`, `age = 20 AND sal > 10`, `sal > 10`],
          1,
          `An equality query gives a constant for every field of the search key. If any field is not a constant, it is a range query.`,
          'concept'
        ),
      ],
    },

    query_processing_tuning: {
      label: 'Query Processing and Physical Design Tuning',
      lectures: 'L04-L05, Tut04',
      practice: [
        S(
          `What is the correct order of the main steps in query processing?`,
          [`Optimization, parsing and translation, evaluation`, `Evaluation, optimization, parsing and translation`, `Parsing and translation, optimization, evaluation`, `Parsing and translation, evaluation, optimization`],
          2,
          `The query is first parsed and translated, then an efficient plan is chosen, and last the plan is executed.`,
          'order'
        ),
        S(
          `A plan reads SP (10,000 pages), selects 50 tuples and keeps them in memory, then reads S (100 pages) to join. How many disk I/Os in total?`,
          [`10,100`, `1,010,000`, `3,000,000`, `100,100`],
          0,
          `10,000 + 100 = 10,100 I/Os. Doing the selection first avoids the huge Cartesian product, which costs about 3,000,000 I/Os.`,
          'calc'
        ),
        S(
          `Reserves (1000 pages) is the outer relation, Sailors has 500 pages, and each outer block is 100 pages. What is the block nested loops cost in I/Os?`,
          [`15,000`, `5,500`, `501,000`, `6,000`],
          3,
          `Cost = scan of outer + number of blocks x scan of inner = 1000 + 10 x 500 = 6000. Using Sailors as outer would give 500 + 5 x 1000 = 5500.`,
          'calc'
        ),
        S(
          `A 108-page file is sorted with 5 buffer pages using external merge sort. What is the I/O cost, using 2N x passes?`,
          [`648`, `864`, `540`, `1,080`],
          1,
          `Pass 0 gives 22 runs, then merging 4 at a time gives 6, 2 and 1 runs, so there are 4 passes. Cost = 2 x 108 x 4 = 864.`,
          'calc'
        ),
        S(
          `A query block has at most 10,000 result tuples. Its two terms have reduction factors 1/10 and 1/5. What is the estimated result size?`,
          [`2,000`, `200`, `1,500`, `8,000`],
          1,
          `Result size = max tuples x product of reduction factors = 10,000 x 1/10 x 1/5 = 200. This assumes the terms are independent.`,
          'calc'
        ),
        S(
          `A query selects Emp rows where salary > 20000. Which index fits best?`,
          [`A hash index on salary`, `A hash index on empno`, `A B+ tree index on salary`, `A hash index on dno`],
          2,
          `A range selection suggests a B+ tree index. Hash indexes help only equality selections.`,
          'scenario'
        ),
        M(
          `What do the system catalogs typically contain?`,
          [`Number of tuples and pages for each relation`, `Number of distinct key values for each index`, `Index height and low and high key values for tree indexes`, `The full text of every query ever run`],
          [0, 1, 2],
          `Catalogs hold statistics that help the optimizer estimate costs. They are updated periodically, not on every data change.`,
          'multi'
        ),
        M(
          `Which statements about index selection are true?`,
          [`An equality selection suggests a hash index`, `A range selection suggests a B+ tree index`, `A hash index is the best choice for range queries`, `A relation can have several clustered indexes`],
          [0, 1],
          `Hash indexes cannot support range searches, and only one index per relation can be clustered.`,
          'multi'
        ),
        M(
          `Which are heuristic rules used to prune the plan space?`,
          [`Push selections down in the query tree`, `Avoid Cartesian products where possible`, `Always use an index when one exists`, `Always sort both relations before any join`],
          [0, 1],
          `Using an index does not always give an efficient plan. The optimizer compares costs instead of using an index blindly.`,
          'multi'
        ),
        M(
          `Which statements about index nested loops join are true?`,
          [`It needs an index on the join column of the inner relation`, `A hash index probe costs about 1.2 I/Os`, `A B+ tree index probe costs about 2 to 4 I/Os`, `The outer relation must be the one with the index`],
          [0, 1, 2],
          `The index is on the inner relation, and the outer relation is scanned. The cost of fetching the matching tuples then depends on clustering.`,
          'multi'
        ),
      ],
      diagnostic: [
        D(
          `R has 1,000 pages and S has 200 pages. With 52 buffer pages, R is the outer relation of a block nested loops join. What is the cost?`,
          [`4,000`, `201,000`, `2,001,000`, `5,000`],
          3,
          `Block size = 52 - 2 = 50 pages, so there are 20 blocks. Cost = 1000 + 20 x 200 = 5,000. The value 4,000 forgets to add the scan of R.`,
          'calc'
        ),
        D(
          `A hash index probe costs 1.2 I/Os. 200 matching Emp tuples fit on 2 pages with a clustered index. About how many I/Os, rounded up?`,
          [`4`, `202`, `201`, `3`],
          0,
          `Cost = 1.2 + 2 = 3.2, rounded up to 4. With an unclustered index it could be about 202 I/Os, one per tuple.`,
          'calc'
        ),
        D(
          `Why can an unclustered index be enough for an index-only plan?`,
          [`Unclustered indexes already store the full data records`, `Only the index entries are scanned, so no tuples are fetched`, `Clustering would sort the index entries a second time`, `The optimizer converts the index into a heap file`],
          1,
          `An index-only plan never reads the data records, so the order of the records (clustering) does not matter.`,
          'concept'
        ),
      ],
    },

    xml_databases: {
      label: 'XML in Databases',
      lectures: 'L06-L06x',
      practice: [
        S(
          `How does XML differ from HTML in its use of tags?`,
          [`XML tags describe only fonts and page layout`, `XML tags are not case sensitive`, `XML does not allow nested tags`, `XML tags describe meaning, such as an address`],
          3,
          `HTML tags are for formatting, but XML tags carry semantics. XML tags are also case sensitive and can be nested.`,
          'compare'
        ),
        S(
          `Which is required for a well-formed XML document?`,
          [`A DTD attached to the document`, `One root tag around all nested tags`, `All tag names written in capitals`, `A schema that validates every element`],
          1,
          `A well-formed document has a declaration and one root tag that surrounds the nested tags. A schema is used for validation, not for well-formedness.`,
          'concept'
        ),
        S(
          `A team has a static, well-structured schema. Which XML storage approach does the lecture say is advantageous?`,
          [`XML-enabled database`, `Native XML database`, `Untyped XML column`, `A CLOB column only`],
          0,
          `With a static schema, an XML-enabled database can reuse mature relational technology. A native XML database suits schemas that are not static.`,
          'scenario'
        ),
        S(
          `What does the XPath expression //PRICE select?`,
          [`Only PRICE elements directly under the root`, `The attribute named PRICE`, `PRICE elements anywhere in the document`, `Only the first PRICE element`],
          2,
          `A path that begins with // can start anywhere, so it finds all PRICE elements in the document.`,
          'concept'
        ),
        S(
          `In XPath, how do you refer to an attribute called name?`,
          [`@name`, `$name`, `#name`, `name()`],
          0,
          `The @ sign is short for the attribute:: axis. The $ sign is used for variables in XQuery.`,
          'concept'
        ),
        S(
          `Which SQL Server XML method returns 1 when the XQuery gives a non-empty node list?`,
          [`query()`, `value()`, `modify()`, `exist()`],
          3,
          `exist() is for existence checks and returns 1 or 0. query() returns XML, value() returns a scalar and modify() changes the XML.`,
          'concept'
        ),
        M(
          `Which of these are XML schema languages?`,
          [`DTD`, `XML Schema`, `RELAX NG`, `XPath`],
          [0, 1, 2],
          `XPath is a language for describing paths in XML documents. It does not describe the structure of a document.`,
          'multi'
        ),
        M(
          `Which statements about the SQL Server XML data type methods are true?`,
          [`query() returns an untyped XML instance`, `value() returns a scalar of a chosen SQL type`, `exist() returns 1 or 0`, `modify() can only read data, never change it`],
          [0, 1, 2],
          `modify() runs XML DML with insert, delete and update keywords, so it can change the XML.`,
          'multi'
        ),
        M(
          `When should you use a typed XML column?`,
          [`You have schemas and want the server to validate the XML`, `You want storage and query optimizations from type information`, `You have no schema for your XML data`, `You have schemas but do not want validation`],
          [0, 1],
          `Untyped XML is for the cases with no schema, or when you do not want the server to validate.`,
          'multi'
        ),
        M(
          `Which statements about XPath axes are true?`,
          [`/BARS/BEER is short for /BARS/child::BEER`, `@ is short for the attribute:: axis`, `// is short for the descendant-or-self:: axis`, `The default axis is parent::`],
          [0, 1, 2],
          `The default axis is child::, which goes to all children of the current nodes.`,
          'multi'
        ),
      ],
      diagnostic: [
        D(
          `You want only the rows whose XML has /doc with id 123. Which WHERE clause is right?`,
          [`WHERE xDoc.modify('/doc[@id = 123]') = 1`, `WHERE xDoc.value('/doc') = 123`, `WHERE xDoc.exist('/doc[@id = 123]') = 1`, `WHERE xDoc.query('/doc') = 1`],
          2,
          `exist() is made for existence checks in a WHERE clause. modify() changes data and query() returns XML, not 1 or 0.`,
          'scenario'
        ),
        D(
          `How are variables written in XQuery?`,
          [`With @ before the name`, `With $ before the name`, `With # before the name`, `With % before the name`],
          1,
          `XQuery variables start with $, for example $prod. The @ sign is used for attributes in XPath.`,
          'concept'
        ),
        D(
          `A catalog has products 557 (dept WMN), 563 (ACC), 443 (ACC), 784 (MEN). Which product number does //product[number > 500][@dept="ACC"] return?`,
          [`443`, `784`, `557`, `563`],
          3,
          `The first predicate keeps 557, 563 and 784. The second keeps only dept ACC, so only 563 remains. Product 443 is ACC but fails number > 500.`,
          'scenario'
        ),
      ],
    },

    transactions_concurrency: {
      label: 'Transactions and Concurrency Control',
      lectures: 'L07-L08',
      practice: [
        S(
          `A transaction committed, then the system crashed and its update was lost. Which ACID property was violated?`,
          [`Isolation`, `Atomicity`, `Consistency`, `Durability`],
          3,
          `Durability means a committed transaction survives crashes. The log and recovery manager are responsible for it.`,
          'scenario'
        ),
        S(
          `Who is mainly responsible for keeping a transaction consistent?`,
          [`The lock manager`, `The recovery manager`, `The user, through the program logic`, `The deadlock detector`],
          2,
          `The DBMS checks integrity constraints, but the program logic must make sure a transaction keeps the data consistent, for example equal totals in a transfer.`,
          'concept'
        ),
        S(
          `Which conflict causes a dirty read, which means reading uncommitted data?`,
          [`WR conflict`, `RW conflict`, `WW conflict`, `RR conflict`],
          0,
          `A dirty read is a write followed by a read of the same object by another transaction. RW gives unrepeatable reads and WW gives overwriting of uncommitted data.`,
          'compare'
        ),
        S(
          `In Strict 2PL, when does a transaction release its locks?`,
          [`Right after each read or write`, `When the transaction completes`, `After it gets its last lock`, `Only when a deadlock is found`],
          1,
          `Strict 2PL holds all locks until the transaction commits or aborts. This is what avoids the conflicts.`,
          'concept'
        ),
        S(
          `Using wound-wait, Ti asks for a lock held by Tj and Ti has higher priority. What happens?`,
          [`Ti aborts`, `Ti waits for Tj`, `Tj aborts`, `Both abort and restart`],
          2,
          `In wound-wait, a higher-priority requester wounds (aborts) the lock holder. In wait-die, the higher-priority requester waits instead.`,
          'compare'
        ),
        S(
          `Which of these is NOT an isolation level in SQL?`,
          [`READ WRITE`, `READ COMMITTED`, `REPEATABLE READ`, `SERIALIZABLE`],
          0,
          `READ ONLY and READ WRITE are access levels. The isolation levels are SERIALIZABLE, REPEATABLE READ, READ COMMITTED and READ UNCOMMITTED.`,
          'not'
        ),
        M(
          `Which statements about Strict 2PL are true?`,
          [`A transaction needs an S lock before reading`, `A transaction needs an X lock before writing`, `If one transaction holds an X lock, no other can lock that object`, `Locks may be released as soon as the object is used`],
          [0, 1, 2],
          `Locks are kept until the transaction completes. Releasing them early would allow conflicts.`,
          'multi'
        ),
        M(
          `Which statements about aborts and recoverability are true?`,
          [`A cascading abort can happen when T2 reads data written by T1 and T1 then aborts`, `Strict 2PL avoids cascading aborts`, `Strict 2PL allows unrecoverable schedules`, `A cascading abort never involves more than one transaction`],
          [0, 1],
          `Strict 2PL does not allow cascading aborts or unrecoverable schedules. One abort can cascade through several transactions.`,
          'multi'
        ),
        M(
          `Which statements about deadlock detection are true?`,
          [`A waits-for graph has transactions as nodes`, `A cycle in the waits-for graph means a deadlock`, `A victim transaction is aborted to break the deadlock`, `A deadlock exists whenever the graph has no edges`],
          [0, 1, 2],
          `An edge Ti to Tj means Ti waits for Tj. A graph with no edges has no waiting at all, so no deadlock.`,
          'multi'
        ),
        M(
          `Which statements about SQL isolation levels are true?`,
          [`REPEATABLE READ can still allow phantoms`, `READ UNCOMMITTED can allow dirty reads`, `READ COMMITTED prevents phantoms`, `SERIALIZABLE allows unrepeatable reads`],
          [0, 1],
          `READ COMMITTED still allows unrepeatable reads and phantoms. SERIALIZABLE uses Strict 2PL plus index locking, so it allows neither.`,
          'multi'
        ),
      ],
      diagnostic: [
        D(
          `Which rule applies to the log when a transaction writes a page?`,
          [`The changed page must reach disk before the log record`, `Log records are written only when a transaction commits`, `Only the new value is logged, never the old value`, `The log record must reach disk before the page`],
          3,
          `The log keeps the old and new values, and its record must be on disk before the changed page. This allows undo after an abort or crash.`,
          'concept'
        ),
        D(
          `Which method locks the index page for rating = 1 to prevent phantoms?`,
          [`Wait-die`, `Index locking`, `Lock escalation`, `Cascading abort`],
          1,
          `Index locking locks the index page where entries with that rating are, or would be. It is a special case of predicate locking.`,
          'concept'
        ),
        D(
          `T1 scans table R and updates a few tuples. Which lock should it take on R?`,
          [`SIX`, `IS`, `S`, `IX`],
          0,
          `SIX acts like S and IX together: T1 reads all of R and takes X locks on a few tuples. IS is for reading only part of R.`,
          'scenario'
        ),
      ],
    },

    nosql_big_data: {
      label: 'NoSQL, MongoDB and Big Data (Hadoop/MapReduce)',
      lectures: 'L09-L09.4',
      practice: [
        S(
          `What is the order of the main phases in a MapReduce job?`,
          [`Mapping, input splits, shuffling, reducing`, `Input splits, shuffling, mapping, reducing`, `Input splits, mapping, shuffling, reducing`, `Input splits, mapping, reducing, shuffling`],
          2,
          `The input is split, each split is mapped, the map output is shuffled to group the same keys, and then the values are reduced.`,
          'order'
        ),
        S(
          `In BASE, what does "soft state" mean?`,
          [`The system is always in a fixed, locked state`, `The system is in flux and changes all the time`, `The system never accepts new writes`, `The system is always fully consistent`],
          1,
          `Soft state means the state can change over time, even without new input, because the system is only eventually consistent.`,
          'concept'
        ),
        S(
          `In the CAP theorem, what does partition tolerance mean?`,
          [`All clients see the same data after an update`, `The system is always on and answers every request`, `The data is split into partitions across tables`, `The system keeps working when server links are unreliable`],
          3,
          `Partition tolerance is about continuing to work when communication between servers is unreliable. The first option describes consistency and the second describes availability.`,
          'concept'
        ),
        S(
          `Which is a drawback of vertical scalability (scaling up)?`,
          [`Problems with synchronization between nodes`, `Higher costs and a limit on data growth`, `Handling partial failure of nodes`, `Keeping many replicas consistent`],
          1,
          `Bigger machines cost more and have a limit. The other options are new problems that come with horizontal scaling.`,
          'compare'
        ),
        S(
          `A read-heavy application needs more read capacity. Which step fits master-slave replication?`,
          [`Move all data onto one shard`, `Add more master nodes for updates`, `Add more slave nodes to serve reads`, `Remove replicas to save space`],
          2,
          `Reads can be served by any node, so more slaves give more read capacity. Updates still go through the single master.`,
          'scenario'
        ),
        S(
          `A recommendation engine works on highly connected data such as friends and purchases. Which NoSQL type fits best?`,
          [`A graph database`, `A key-value store`, `A document database`, `A column-family store`],
          0,
          `Graph databases suit connected data such as social networks and recommendations. Nodes know their neighbours, so each hop stays cheap.`,
          'scenario'
        ),
        M(
          `Which NoSQL types are aggregate-oriented?`,
          [`Key-value stores`, `Document stores`, `Column-family stores`, `Graph databases`],
          [0, 1, 2],
          `Key-value, document and column-family stores work with aggregates. Graph databases store nodes and edges.`,
          'multi'
        ),
        M(
          `Which statements about MongoDB are true?`,
          [`$gte means greater than or equal to`, `By default update changes only one document`, `In a projection, 1 includes a field and 0 excludes it`, `All documents in a collection must have the same fields`],
          [0, 1, 2],
          `Each document in a collection can have its own set of fields. To update many documents you pass {multi : true}.`,
          'multi'
        ),
        M(
          `Which are key benefits of MapReduce?`,
          [`It moves the computation to where the data is stored`, `It can re-run a failed sub-task using another copy of the data`, `It can process petabytes of data stored in HDFS`, `It copies all input data to one central server first`],
          [0, 1, 2],
          `MapReduce moves compute to the data, which reduces network I/O. Copying all data to one server is the opposite.`,
          'multi'
        ),
        M(
          `Which are core modules in the Hadoop architecture?`,
          [`HDFS`, `YARN`, `MapReduce`, `Oozie`],
          [0, 1, 2],
          `The core modules are HDFS, YARN, MapReduce and common utilities. Oozie (job scheduling) belongs to the wider Hadoop ecosystem.`,
          'multi'
        ),
      ],
      diagnostic: [
        D(
          `Which command changes only the weight of Roooooodles to 590?`,
          [`db.unicorns.update({name:"Roooooodles"},{weight:590})`, `db.unicorns.update({name:"Roooooodles"},{$inc:{weight:590}})`, `db.unicorns.update({weight:590},{name:"Roooooodles"})`, `db.unicorns.update({name:"Roooooodles"},{$set:{weight:590}})`],
          3,
          `$set changes only the named field. Without it, the second argument is treated as a whole replacement document, and $inc would add 590 to the old weight.`,
          'scenario'
        ),
        D(
          `An update on name "Walala" did nothing because no such document exists. What makes it insert one?`,
          [`Pass {upsert : true} as the third argument`, `Pass {multi : true} as the third argument`, `Use $set instead of $inc`, `Call find() before the update`],
          0,
          `An upsert updates the document if found and inserts it if not. It is enabled with the third parameter.`,
          'scenario'
        ),
        D(
          `Which Hadoop node keeps the file location information for HDFS?`,
          [`Data Node`, `Task Tracker`, `Name Node`, `Job Tracker`],
          2,
          `The Name Node stores where data is located. The Data Nodes store the data itself.`,
          'concept'
        ),
      ],
    },
  },
};
