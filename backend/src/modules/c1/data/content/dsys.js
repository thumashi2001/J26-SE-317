import { S, M, D } from './helpers.js';
export default {
  semester: 'Y3S2',
  module_code: 'SE3020',
  module_name: 'Distributed Systems',
  topics: {
    ds_architectures_sockets: {
      label: 'Distributed Architectures and Socket Programming',
      lectures: 'L01-L03',
      practice: [
        S(
          'Which statement best describes a distributed system?',
          [
            'Components on networked computers coordinate their actions only by passing messages',
            'Several processors that share one memory and use one common clock',
            'One powerful computer that serves many users through terminals',
            'A network that only moves packets between addressed machines',
          ],
          0,
          'In a distributed system the components run on networked computers and coordinate only through messages. Shared memory describes a multiprocessor, and packet moving describes a network.',
          'concept'
        ),
        S(
          'How does a distributed system differ from a computer network?',
          [
            'A network hides all computers, but a distributed system shows every address',
            'In a network the machines are visible and addressed, but a distributed system makes them transparent',
            'A network focuses on applications, but a distributed system focuses on routing',
            'A distributed system never depends on the services of a network',
          ],
          1,
          'Network entities are explicitly addressed (for example by IP address). A distributed system hides the many computers from the user. Every distributed system still relies on a network.',
          'compare'
        ),
        S(
          'Two customers try to buy the last seat in an online course at the same moment. Which challenge does this show?',
          [
            'Heterogeneity',
            'Scalability',
            'Concurrency',
            'Openness',
          ],
          2,
          'Shared access to a resource by many users at once is a concurrency problem. The system must keep the data correct.',
          'scenario'
        ),
        S(
          'Which of these is NOT a distribution transparency named in the lecture?',
          [
            'Location transparency',
            'Replication transparency',
            'Migration transparency',
            'Compilation transparency',
          ],
          3,
          'The lecture lists access, location, failure, replication, migration, concurrency, performance, scaling, persistence and transaction transparency. There is no compilation transparency.',
          'not'
        ),
        S(
          'Compared with client-server, which statement about peer-to-peer (P2P) systems is correct?',
          [
            'P2P avoids a single point of failure, but finding resources is harder',
            'P2P is simpler to build because peers never join or leave',
            'P2P makes resource lookup faster than a central server',
            'P2P always needs a dedicated server for every request',
          ],
          0,
          'P2P spreads data and work across peers, so there is no single point of failure. The cost is harder resource discovery and slower lookup. Peer join and churn also make it more complex.',
          'compare'
        ),
        S(
          'Which order is correct for setting up a TCP connection between a client and a server?',
          [
            'Client requests, server listens, server accepts, data transfer',
            'Server listens, client requests a connection, server accepts, data transfer',
            'Server accepts, server listens, client requests, data transfer',
            'Client requests, data transfer, server listens, server accepts',
          ],
          1,
          'The passive server first listens, then the active client requests a connection, and the server accepts it. Data transfer starts after that, on the new socket.',
          'order'
        ),
        M(
          'Which are characteristics of distributed systems?',
          [
            'Tasks run concurrently',
            'Components communicate by message passing',
            'Every process knows the current global state',
            'There is no single global clock',
          ],
          [0, 1, 3],
          'Distributed systems have concurrency, message passing, independent failures and no global clock. No single process can know the global state of the whole system.',
          'multi'
        ),
        M(
          'Which are examples of hybrid system architectures?',
          [
            'Edge-server systems such as ISPs',
            'Collaborative systems such as BitTorrent',
            'Structured P2P systems such as Chord',
            'A thin client talking to one central server',
          ],
          [0, 1],
          'Hybrid architectures combine client-server and P2P ideas, as in edge-server and collaborative systems. Chord is a structured P2P system, and a thin client with one server is plain client-server.',
          'multi'
        ),
        M(
          'Which statements about Java TCP sockets are correct?',
          [
            'ServerSocket waits for incoming connection requests',
            'accept() gives a new socket for the accepted connection',
            'A TCP socket has no notion of a connection',
            'Only one process can listen on a given TCP port',
          ],
          [0, 1, 3],
          'ServerSocket is the passive socket and accept() returns a new connection socket. TCP is connection-oriented, so the third statement describes UDP instead.',
          'multi'
        ),
        M(
          'Which statements about UDP sockets in Java are correct?',
          [
            'No welcoming socket is needed',
            'DatagramPacket carries the data and the destination address',
            'Packets can be lost or arrive out of order',
            'The server must call accept() before reading data',
          ],
          [0, 1, 2],
          'UDP is connectionless, so there is no handshake and no accept(). Packets are sent with DatagramSocket and DatagramPacket and delivery is not guaranteed.',
          'multi'
        ),
      ],
      diagnostic: [
        D(
          'A company splits its web application into presentation, business and data tiers. Which is a disadvantage of this tiering?',
          [
            'Code can no longer be reused across the tiers',
            'The system cannot be scaled at any tier',
            'Communication overhead and complexity go up',
            'Fault tolerance becomes impossible in a tiered system',
          ],
          2,
          'Tiering helps reuse, scalability, integrity and fault tolerance. The costs are more communication overhead, possible message loss, security risks and extra complexity.',
          'scenario'
        ),
        D(
          'A live video app cares more about speed than about guaranteed delivery. Which choice fits best?',
          [
            'TCP, because it guarantees delivery',
            'TCP, because it is connection-oriented',
            'FTP, because it transfers files reliably',
            'UDP, because speed matters more than assurance',
          ],
          3,
          'UDP is used for streaming and multicast when speed is more important than guaranteed delivery. TCP is used when guaranteed delivery is required.',
          'scenario'
        ),
        D(
          'What does the Chord finger table improve?',
          [
            'It reduces lookup time to O(log n)',
            'It removes the need for peer IDs',
            'It stops peers from leaving the network',
            'It stores all data on one super-peer',
          ],
          0,
          'The finger table lets a peer jump ahead in the ring, so lookup time falls to O(log n). It does not prevent churn.',
          'concept'
        ),
      ],
    },

    ds_rpc_messaging: {
      label: 'RPC/RMI and Asynchronous Communication',
      lectures: 'L04-L05',
      practice: [
        S(
          'What does a Remote Procedure Call (RPC) allow a client to do?',
          [
            'Call a procedure on a remote computer as if it were a local call',
            'Share variables directly with a remote process in memory',
            'Send events to many subscribers through a topic',
            'Copy a whole program to the server before running it',
          ],
          0,
          'RPC hides the network so a remote procedure looks like a local one. Stubs handle the message passing.',
          'concept'
        ),
        S(
          'How does Java RMI differ from basic RPC?',
          [
            'RMI handles only procedure calls and ignores objects',
            'RMI works with remote objects, but RPC does not',
            'RMI needs no interface, but RPC always needs one',
            'RMI works only inside a single JVM',
          ],
          1,
          'RPC addresses procedure calls only. RMI adds objects (Objects + RPC = RMI), so methods are invoked on remote objects between different JVMs.',
          'compare'
        ),
        S(
          'In RPC, a client stub procedure is similar to which element of RMI?',
          [
            'The skeleton',
            'The RMI registry',
            'The proxy',
            'The transport layer',
          ],
          2,
          'The client stub is like the RMI proxy, and the server stub is like the RMI skeleton.',
          'concept'
        ),
        S(
          'Which of these is NOT a strength of Java RMI listed in the lecture?',
          [
            'It can pass complex objects, not only primitive types',
            'It runs on any machine that has a JVM',
            'It includes distributed garbage collection',
            'It has good support for legacy C and C++ systems',
          ],
          3,
          'RMI is tied to Java and does not support legacy systems written in C or C++ well. That is listed as a weakness.',
          'not'
        ),
        S(
          'A client needs temperature updates only when the value changes. Polling wastes resources. What is a better design?',
          [
            'Register a callback so the server notifies the client on change',
            'Block the client until the server finishes a long job each time',
            'Ask the server every second until the value is different',
            'Use two separate clients that both poll the server in turn',
          ],
          0,
          'With a callback the client registers with the server, and the server calls back when the event happens. Polling repeats requests, and blocking wastes the client.',
          'scenario'
        ),
        S(
          'In JMS, which pair correctly describes the two messaging domains?',
          [
            'Point-to-point sends each message to many consumers, and publish-subscribe sends each message to only one',
            'Point-to-point uses queues with one receiver per message, and publish-subscribe uses topics',
            'Both domains use topics, but only publish-subscribe also uses queues for delivery',
            'Both domains deliver every message to all consumers that are connected',
          ],
          1,
          'Point-to-point is built on queues and each message has only one consumer. Publish-subscribe uses a topic and each message can reach many consumers.',
          'compare'
        ),
        M(
          'Which are strengths of Java RMI?',
          [
            'It can pass complex objects',
            'It is portable to any machine with a JVM',
            'It has distributed garbage collection',
            'It interoperates with any programming language',
          ],
          [0, 1, 2],
          'RMI is object oriented, portable and has distributed garbage collection. It is Java-centric, so it does not interoperate with any language.',
          'multi'
        ),
        M(
          'To provide a client callback in RMI, what must the client side do?',
          [
            'Supply a remote interface for the callback',
            'Create an object that implements that interface',
            'Pass a reference to that object to the server',
            'Poll the server repeatedly for new events',
          ],
          [0, 1, 2],
          'The client defines a remote callback interface, implements it and passes the reference to the server in a remote call. The server stores it and calls back later.',
          'multi'
        ),
        M(
          'Which JMS message types are paired correctly with their content?',
          [
            'TextMessage: a String',
            'MapMessage: a set of name/value pairs',
            'BytesMessage: a stream of primitive values',
            'ObjectMessage: a serialized object',
          ],
          [0, 1, 3],
          'BytesMessage holds a stream of uninterpreted bytes. A stream of primitive values is a StreamMessage.',
          'multi'
        ),
        M(
          'Which are JMS features described in the lecture?',
          [
            'Durable subscriptions keep messages until they are received or expire',
            'Message selectors use SQL-like syntax on message headers',
            'Transacted sessions can commit or roll back',
            'onMessage() runs only when the client calls receive()',
          ],
          [0, 1, 2],
          'onMessage() is called by the JMS provider when a message arrives and a listener is registered. The receive() method is the synchronous way to fetch messages.',
          'multi'
        ),
      ],
      diagnostic: [
        D(
          'A GUI client calls a server function that does heavy disk work. How should the call be made?',
          [
            'Synchronously, so the user always waits for the result',
            'Synchronously, because all RPC calls must block',
            'Asynchronously, so the GUI stays responsive',
            'It cannot be called remotely at all',
          ],
          2,
          'Asynchronous calls are best for long-running functions and for keeping a GUI responsive. Making every call asynchronous adds code complexity, so use it where needed.',
          'scenario'
        ),
        D(
          'In the RMI layered structure, which layer contains the RMI registry?',
          [
            'Application layer',
            'Transport layer',
            'Interface layer',
            'Remote reference layer',
          ],
          3,
          'The lecture places the application (server, client), the interface (stub, skeleton), the remote reference layer (registry) and the transport layer (TCP/IP) in separate layers.',
          'concept'
        ),
        D(
          'Which phone analogy describes a callback?',
          [
            'Calling and leaving a message for the other party to call back',
            'Calling and waiting on the line until the other party answers',
            'Calling again and again to see if the other party is free',
            'Calling many people at once with the same message',
          ],
          0,
          'Blocking is waiting on the line, polling is calling repeatedly, and callback is leaving a message to be called back.',
          'compare'
        ),
      ],
    },

    ds_components_formats: {
      label: 'Component Frameworks and Open Message Formats',
      lectures: 'L06-L07',
      practice: [
        S(
          'In the software component model, what plays the role of the pins of a chip?',
          [
            'Interfaces',
            'Containers',
            'Databases',
            'Compilers',
          ],
          0,
          'The pins of software components are their interfaces, which are sets of methods. Integrators connect components using these interface descriptions.',
          'concept'
        ),
        S(
          'How do local and remote EJB interfaces differ?',
          [
            'Local passes parameters by value across JVMs, and remote passes parameters by reference inside one JVM',
            'Local is for calls in the same JVM (by reference), and remote is for calls across JVMs (by value)',
            'Local is only for entity beans, and remote is only for session beans, with no other differences',
            'Both pass parameters by reference, but only the remote interface needs an annotation in the bean class',
          ],
          1,
          'A local interface (@Local) is used inside the same JVM with parameters by reference. A remote interface (@Remote) is used across JVMs and parameters are serialized, so they are passed by value.',
          'compare'
        ),
        S(
          'A shopping cart must remember the items of one client across several calls. Which EJB fits best?',
          [
            'Stateless session bean',
            'Message-driven bean',
            'Stateful session bean',
            'Entity bean without a key',
          ],
          2,
          'A stateful session bean keeps conversational state and each instance is bound to one client session. Stateless beans are pooled and serve many clients.',
          'scenario'
        ),
        S(
          'Which of these is NOT one of the major EJB component types?',
          [
            'Session bean',
            'Entity bean',
            'Message-driven bean',
            'Transaction bean',
          ],
          3,
          'The three major types are session beans, entity beans and message-driven beans. Transactions are a service provided by the container.',
          'not'
        ),
        S(
          'An XML file has all tags closed and nested correctly, but it uses a tag that its XSD does not define. How is it described?',
          [
            'Well-formed but not valid',
            'Valid but not well-formed',
            'Neither well-formed nor valid',
            'Both well-formed and valid',
          ],
          0,
          'Well-formed means the general XML syntax rules are followed. Valid means the document also follows the XSD, so an undefined tag makes it invalid.',
          'scenario'
        ),
        S(
          'Which is a known drawback of JSON compared with XML?',
          [
            'It cannot be read by people without a special tool',
            'It has no namespaces and no built-in validation',
            'It is slower and heavier than XML in practice',
            'It works only with the Java language',
          ],
          1,
          'JSON is lighter and faster than XML, but it lacks namespaces and built-in schema validation. It is language independent.',
          'compare'
        ),
        M(
          'Which statements about CORBA are correct?',
          [
            'The IDL compiler generates stubs and skeletons',
            'IIOP lets ORBs from different vendors interoperate',
            'The naming service lets clients find objects by name',
            'The specification is small, which made CORBA easy to adopt',
          ],
          [0, 1, 2],
          'CORBA never caught on partly because its specification is huge and complex. The other three statements are true.',
          'multi'
        ),
        M(
          'Which statements about XML are correct?',
          [
            'Element names are case sensitive',
            'Element names cannot contain spaces',
            'Element names may start with a number',
            'A document must have exactly one root element',
          ],
          [0, 1, 3],
          'XML is strict: names are case sensitive, cannot contain spaces and cannot start with a number or punctuation. A document has one and only one root element.',
          'multi'
        ),
        M(
          'Which are advantages of binary formats over XML?',
          [
            'Smaller data size',
            'No need to convert between text and numbers',
            'Simpler to parse',
            'Self-describing and platform neutral',
          ],
          [0, 1, 2],
          'Binary formats are smaller, faster and simpler to parse. Being self-describing and platform neutral is an advantage of XML.',
          'multi'
        ),
        M(
          'Which statements about JSON are correct?',
          [
            'Strings are written in double quotes',
            'Objects are unordered name/value pairs inside braces',
            'Arrays are ordered values inside square brackets',
            'Numbers can be written in hexadecimal',
          ],
          [0, 1, 2],
          'JSON numbers can be integer, real or scientific. There is no octal or hex, and no NaN or Infinity.',
          'multi'
        ),
      ],
      diagnostic: [
        D(
          'Two vendors both use a table element in one XML document. What avoids the name conflict?',
          [
            'Writing all tags in capital letters',
            'Moving the data into an XSD file',
            'Using XML namespaces with prefixes',
            'Removing the XML declaration',
          ],
          2,
          'A namespace, declared with xmlns:prefix and a URI, makes names like h:table and f:table different. Case alone is not a reliable fix.',
          'scenario'
        ),
        D(
          'Which technology is used to transform an XML document into HTML for display?',
          [
            'XSD',
            'JAXB',
            'DTD',
            'XSLT',
          ],
          3,
          'XSLT holds the formatting information and, applied to XML, can produce HTML. XSD describes structure, and JAXB generates schemas from classes.',
          'concept'
        ),
        D(
          'How is a message-driven EJB invoked?',
          [
            'Asynchronously, when a message arrives',
            'Directly by clients through a remote interface',
            'Only by another bean in the same JVM',
            'By a web browser through a WAR file',
          ],
          0,
          'A message-driven bean is triggered by messages (for example JMS) and cannot be invoked through local or remote interfaces. It is stateless and transaction aware.',
          'concept'
        ),
      ],
    },

    ds_soa_web_services: {
      label: 'SOA, Web Services and Service Integration',
      lectures: 'L08-L09',
      practice: [
        S(
          'Why do traditional RPC frameworks cause firewall problems on the Internet?',
          [
            'Each component uses its own port, so many firewall holes are needed',
            'They send all data in plain text, which firewalls always block outright',
            'They use one shared port, which firewalls therefore cannot filter at all',
            'They never use TCP, so firewalls drop all of their traffic by default',
          ],
          0,
          'RPC frameworks give each server component its own port. For Internet access an administrator would have to open one hole per component, and they are reluctant to do that.',
          'concept'
        ),
        S(
          'What most clearly distinguishes SOA from other architectures?',
          [
            'Tight coupling between client and server',
            'Loose coupling through well-defined interfaces',
            'Embedding calls between services in their source code',
            'Using only one programming language',
          ],
          1,
          'In SOA the client is independent of the service implementation and talks through a specified interface.',
          'concept'
        ),
        S(
          'Which application is a poor fit for SOA?',
          [
            'A system that crosses platform boundaries',
            'Payment logic that changes often and is reused',
            'A small single-machine app with a short deployed life',
            'A system that crosses trust boundaries',
          ],
          2,
          'SOA suits crossing platform or trust boundaries and reusable logic that changes often. It is poor for non-distributed applications and applications with a short life.',
          'scenario'
        ),
        S(
          'Which statement about SOAP and WSDL is correct?',
          [
            'SOAP describes the service interface, and WSDL defines the message envelope',
            'SOAP is an architectural pattern, and WSDL is a transport protocol',
            'Both are JSON-based formats used only with REST',
            'SOAP defines an XML message structure, and WSDL describes the service in XML',
          ],
          3,
          'SOAP is XML based with an Envelope containing a Header and a Body. WSDL describes a web service in XML, including messages and transports.',
          'compare'
        ),
        S(
          'In a RESTful service, which request removes the user sam?',
          [
            'DELETE on the URI of user sam',
            'POST to the URI of user sam',
            'GET on the URI of user sam',
            'PUT to the URI of all users',
          ],
          0,
          'REST maps POST to create, GET to read, PUT to update or create, and DELETE to delete.',
          'scenario'
        ),
        S(
          'How do orchestration and choreography differ?',
          [
            'Choreography uses a central coordinator for the whole flow, and orchestration does not',
            'Orchestration has one central coordinator, and choreography has none',
            'Both styles always require a central coordinator to run',
            'Orchestration can only be used with REST services',
          ],
          1,
          'Orchestration is an executable process under the control of a single endpoint. In choreography each service knows when to act and with whom to interact.',
          'compare'
        ),
        M(
          'Which are characteristics of SOA?',
          [
            'Services are loosely coupled',
            'Services are stateless',
            'Each service embeds direct calls to other services',
            'Services are contract-based',
          ],
          [0, 1, 3],
          'SOA services have no calls to each other embedded in their code. Protocols and orchestration link them instead.',
          'multi'
        ),
        M(
          'Which statements about securing web services are correct?',
          [
            'Base64 in HTTP Basic Auth is encoding, not encryption',
            'TLS adds transport level confidentiality and integrity',
            'WS-Security gives message level security for SOAP',
            'HTTP Digest Auth sends the password in plain text',
          ],
          [0, 1, 2],
          'Digest Auth sends a hash that includes a nonce instead of the plain password. Basic Auth only Base64-encodes the credentials, so it needs TLS.',
          'multi'
        ),
        M(
          'Which BPEL activity descriptions are correct?',
          [
            'receive waits for an incoming request',
            'invoke calls a web service',
            'flow runs activities in parallel',
            'sequence runs activities in parallel',
          ],
          [0, 1, 2],
          'sequence runs activities in order, while flow runs them in parallel. receive, invoke, assign and throw are primitive activities.',
          'multi'
        ),
        M(
          'Which tasks does SOA governance help with?',
          [
            'Versioning the services',
            'Tracking the quality of service (QoS)',
            'Writing the internal code of every service',
            'Managing the service lifecycle',
          ],
          [0, 1, 3],
          'Governance is about control: listing, versioning, securing, monitoring and managing the lifecycle of services. A service registry is central to it.',
          'multi'
        ),
      ],
      diagnostic: [
        D(
          'What is the role of an Enterprise Service Bus (ESB) in integration?',
          [
            'It stores all business data for every service',
            'It replaces the need for any service interfaces',
            'It routes, transforms and mediates between services and applications',
            'It only encrypts messages between browsers and servers',
          ],
          2,
          'An ESB implements a communication system between interacting applications in an SOA. It routes messages, transforms formats and mediates between different protocols.',
          'concept'
        ),
        D(
          'Which order is correct for HTTP Digest authentication?',
          [
            'Server sends a hash, client sends a nonce, server sends the data, client verifies',
            'Client sends a hash, server sends a nonce, client sends a request, server verifies',
            'Server sends a nonce, client sends a request, server sends a hash, client verifies',
            'Client sends a request, server sends a nonce and realm, client sends a hash, server checks it and replies',
          ],
          3,
          'The client requests, the server answers with a nonce and a realm, the client replies with a hash of the nonce, username, password and realm, and the server compares the hashes.',
          'order'
        ),
        D(
          'Why is a stateless REST service easier to scale?',
          [
            'Every request runs in isolation, so the server stores no state between requests',
            'The server remembers each client, so it can skip authentication',
            'All requests are sent to one fixed server for session handling',
            'Each client must keep a permanent connection open',
          ],
          0,
          'Statelessness means no state is stored on the server and each HTTP request executes in isolation. This makes the service simpler to design and easier to scale.',
          'concept'
        ),
      ],
    },

    ds_cloud_microservices: {
      label: 'Cloud Computing and Microservices',
      lectures: 'L10-L11',
      practice: [
        S(
          'What does elasticity mean in cloud computing?',
          [
            'Capacity can scale up or down on demand',
            'Resources are fixed once they are bought',
            'Software must be installed on a local machine',
            'Users must pay a large fee before use',
          ],
          0,
          'Cloud computing offers pay-as-you-go, self-service and elastic capacity that scales up and down on demand. Fixed provisioning leads to under or over-provisioning.',
          'concept'
        ),
        S(
          'A team adds more machines to its pool of resources when load grows. What is this called?',
          [
            'Vertical scaling (scale up)',
            'Scaling out (horizontal)',
            'Virtual storage pooling',
            'Self-healing of failed nodes',
          ],
          1,
          'Horizontal scaling adds more machines or instances (scale out). Vertical scaling adds CPU or RAM to an existing machine (scale up).',
          'compare'
        ),
        S(
          'A company rents a managed Tomcat platform from a cloud provider. Which service model is this?',
          [
            'IaaS',
            'SaaS',
            'PaaS',
            'DaaS',
          ],
          2,
          'PaaS gives a platform, such as Tomcat, managed by the cloud. IaaS gives infrastructure such as disk space and machines, and SaaS gives software.',
          'scenario'
        ),
        S(
          'Which description matches grid computing?',
          [
            'Tightly coupled identical machines on one LAN acting as one server',
            'A single machine upgraded with more CPU and RAM',
            'A browser that runs all processing on the client',
            'Loosely coupled, mixed resources shared by many organisations',
          ],
          3,
          'Grids are autonomous, dynamic resources contributed by multiple organisations. They are loosely coupled and geographically dispersed. Clusters are usually linked over a LAN and appear as one server.',
          'compare'
        ),
        S(
          'Which is NOT a problem of monolithic architecture?',
          [
            'Parts of the application can be deployed independently',
            'The whole application must be redeployed to update a part',
            'One unstable service can bring the whole application down',
            'Scaling is hard when parts have conflicting resource needs',
          ],
          0,
          'In a monolith everything is developed and deployed as one unit. Independent deployment is a benefit of microservices.',
          'not'
        ),
        S(
          'In microservices, the order service needs data owned by the payment service. What should it do?',
          [
            'Read the payment service database directly',
            'Call the payment service through its API',
            'Copy the payment database into its own schema by hand',
            'Share one central database with every service',
          ],
          1,
          'Each microservice has a private database and can only access its own. Other data is reached through the owning service API.',
          'scenario'
        ),
        M(
          'Which statements about hypervisors are correct?',
          [
            'Type 1 runs directly on the hardware',
            'Type 2 runs as an application on an existing operating system',
            'Type 1 runs as an application on an existing operating system',
            'Type 2 is called a bare-metal hypervisor',
          ],
          [0, 1],
          'Type 1 is the bare-metal hypervisor. Type 2 operates as an application on top of an existing OS.',
          'multi'
        ),
        M(
          'Which statements about fixed resource provisioning are correct?',
          [
            'Under-provisioning gives slow responses',
            'Over-provisioning wastes resources',
            'Demand can change over different time scales',
            'Fixed provisioning always matches the demand',
          ],
          [0, 1, 2],
          'Demand varies, for example over a year or within 90 minutes. Fixed provisioning therefore leads to under or over-provisioning, which autoscaling helps to avoid.',
          'multi'
        ),
        M(
          'Which statements about microservices are correct?',
          [
            'Each microservice can have its own private database',
            'Circuit breaker, timeout and bulkhead help handle failures',
            'A central ESB should hold all business logic',
            'Services connect through simple, lightweight messaging',
          ],
          [0, 1, 3],
          'Microservices move the smart logic into the services and use simple pipes, so a central ESB with all the logic is not the microservices approach.',
          'multi'
        ),
        M(
          'Which statements about OAuth 2.0 and OpenID Connect are correct?',
          [
            'An OAuth 2.0 access token is opaque and holds no user information',
            'OpenID Connect adds an ID token with user information',
            'The ID token is implemented as a signed JWT',
            'The access token carries the full user profile inside it',
          ],
          [0, 1, 2],
          'The access token is a by-reference token that points to user information held by the authorization server. The JWT ID token is by-value.',
          'multi'
        ),
      ],
      diagnostic: [
        D(
          'What does a service registry hold in a microservices system?',
          [
            'The private databases of all of the services',
            'The full source code of every single service',
            'The service instances and where they run',
            'The passwords of all users of the system',
          ],
          2,
          'A service registry holds the microservice instances and their locations. Service discovery is the process of finding the available services.',
          'concept'
        ),
        D(
          'How can a mandatory transaction requirement be met across several microservices?',
          [
            'With one distributed transaction over every database',
            'By sharing a single database between all services',
            'By locking all services until the work is done',
            'With compensating operations',
          ],
          3,
          'Distributed transactions across microservices are too complex. The architecture favours transaction-less coordination, and compensating operations cover mandatory cases.',
          'concept'
        ),
        D(
          'Which tool manages a cluster of Docker containers across hosts, with service discovery and replication control?',
          [
            'Kubernetes',
            'Swagger',
            'JMS',
            'Hypervisor Type 2',
          ],
          0,
          'Kubernetes extends Docker by managing containers across multiple hosts as one system. Docker packages each service as a container image.',
          'concept'
        ),
      ],
    },

    ds_fault_tolerance_clocks: {
      label: 'Fault Tolerance and Clock Synchronization',
      lectures: 'L12-L13',
      practice: [
        S(
          'Which statement about faults, errors and failures is correct?',
          [
            'A fault is the cause of an error',
            'A failure is the cause of a fault',
            'An error is always visible to the user',
            'A fault and a failure mean the same thing',
          ],
          0,
          'A fault causes an error in the system state. A system failure happens only when the error reaches the service interface and the derived service deviates from the specified service.',
          'concept'
        ),
        S(
          'A system has 99.99% availability (four nines). About how much downtime is that per year?',
          [
            '8.76 hours',
            '52.6 minutes',
            '5.26 minutes',
            '3.65 days',
          ],
          1,
          'From the availability table, 99.99% gives about 52.6 minutes per year. 99.9% gives 8.76 hours and 99.999% gives 5.26 minutes.',
          'calc'
        ),
        S(
          'A client sent a request at local time 10:00:00.000 and got the reply at 10:00:00.200. The server time in the reply was 10:00:05.000. Using Cristian\'s algorithm, what time should the client set?',
          [
            '10:00:05.200',
            '10:00:04.900',
            '10:00:05.100',
            '10:00:05.000',
          ],
          2,
          'The round-trip time is 200 ms. Cristian sets the server time plus half the round trip: 5.000 s + 0.100 s = 10:00:05.100.',
          'calc'
        ),
        S(
          'In the Berkeley algorithm the master clock reads 3:00, slave A reads 3:25 and slave B reads 2:50. The average includes the master. By how much does the master tell slave A to adjust?',
          [
            '+5 minutes',
            '-5 minutes',
            '+20 minutes',
            '-20 minutes',
          ],
          3,
          'The differences from the master are 0, +25 and -10, so the average is (0 + 25 - 10) / 3 = +5 minutes. The new time is 3:05, so A moves from 3:25 to 3:05, which is -20 minutes.',
          'calc'
        ),
        S(
          'Using Lamport clocks, process P2 has counter 5. It receives a message with timestamp 2. What is its new counter?',
          [
            '6',
            '3',
            '7',
            '5',
          ],
          0,
          'On a receive, the counter becomes max(local, message) + 1 = max(5, 2) + 1 = 6.',
          'calc'
        ),
        S(
          'With vector clocks, process 2 has V = (2,1,0). It receives a message with vector (3,0,1). What is its new vector?',
          [
            '(3,1,1)',
            '(3,2,1)',
            '(2,2,1)',
            '(3,2,0)',
          ],
          1,
          'Take the component-wise maximum for the other entries: max(2,3) = 3 and max(0,1) = 1. Then add 1 to its own entry: 1 + 1 = 2. The result is (3,2,1).',
          'calc'
        ),
        M(
          'Which statements about two-phase commit (2PC) are correct?',
          [
            'The coordinator starts by sending VOTE_REQUEST to the members',
            'GLOBAL_COMMIT is sent only if all members voted to commit',
            'It is a blocking protocol if the coordinator crashes',
            'GLOBAL_COMMIT is sent when a majority votes to commit',
          ],
          [0, 1, 2],
          'If even one member votes abort, the coordinator sends GLOBAL_ABORT. A majority is not enough.',
          'multi'
        ),
        M(
          'Which failure types are described correctly?',
          [
            'Crash failure: a server halts but worked correctly until then',
            'Timing failure: the response lies outside the specified time interval',
            'Omission failure: the server returns a wrong value',
            'Arbitrary failure: a server may give arbitrary responses at arbitrary times',
          ],
          [0, 1, 3],
          'An omission failure means the server fails to respond, to receive or to send messages. A wrong value is a value failure, which is a response failure.',
          'multi'
        ),
        M(
          'Which statements about clocks and time synchronization are correct?',
          [
            'Clock skew is the difference between the clock values of two processes',
            'Clock drift is the difference in the rates of two clocks',
            'NTP uses a tree of time servers whose root is in touch with UTC',
            'The Berkeley master must have a UTC receiver',
          ],
          [0, 1, 2],
          'The Berkeley algorithm is suited to systems where no machine has a UTC receiver. The master time is set by an operator and the clocks are averaged.',
          'multi'
        ),
        M(
          'Which statements about Lamport and vector clocks are correct?',
          [
            'If a happens before b, then L(a) < L(b)',
            'L(a) < L(b) does not always mean a happened before b',
            'Vector clocks can show that two events are concurrent',
            'Logical clocks must stay close to real UTC time',
          ],
          [0, 1, 2],
          'Logical clocks give an order of events, so internal consistency matters, not closeness to real time. Lamport clocks cannot tell concurrent events apart from ordered ones, but vector clocks can.',
          'multi'
        ),
      ],
      diagnostic: [
        D(
          'A clock has a maximum drift rate of 0.00001 seconds per second. To keep any two clocks within 0.01 seconds of each other, how often must they be synchronized at least?',
          [
            'Every 1000 seconds',
            'Every 250 seconds',
            'Every 500 seconds',
            'Every 50 seconds',
          ],
          2,
          'Two clocks drifting in opposite directions can differ by 2 x rate x time. The interval must be at most 0.01 / (2 x 0.00001) = 500 seconds.',
          'calc'
        ),
        D(
          'In Cristian\'s algorithm the round-trip time is 20 ms and the minimum one-way transmission time is 4 ms. What is the accuracy of the estimate?',
          [
            '+/- 10 ms',
            '+/- 16 ms',
            '+/- 8 ms',
            '+/- 6 ms',
          ],
          3,
          'The accuracy is +/- (Tround / 2 - min) = 20 / 2 - 4 = 6 ms.',
          'calc'
        ),
        D(
          'A system must keep working when 2 processes crash (crash failures). How many replicas are needed by the k+1 rule?',
          [
            '3',
            '5',
            '2',
            '4',
          ],
          0,
          'A system is k fault-tolerant if it survives k faulty processes. For crash failures it needs k + 1 replicas, so k = 2 gives 3 replicas.',
          'calc'
        ),
      ],
    },
  },
};
