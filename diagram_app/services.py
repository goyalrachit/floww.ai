import chromadb
import os
from django.conf import settings
import requests
import json
from .models import ChatMessage, ChatSession
from sentence_transformers import SentenceTransformer
import logging


os.environ["HF_HOME"] = "/data/huggingface"
os.environ["TRANSFORMERS_CACHE"] = "/data/huggingface/models"


# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class ContextAwareMermaidGenerator:
    def __init__(self):
        # Initialize Chroma client
        chroma_path = os.getenv("CHROMA_DB_PATH", "/data/chroma")
        self.chroma_client = chromadb.PersistentClient(path=chroma_path)

        self.collection = self.chroma_client.get_or_create_collection(name="mermaid_prompts")
        
        # Initialize sentence transformer for embeddings
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Define prompt chunks
        self.prompt_chunks = {
            "general_instructions": """
                You are an expert Mermaid diagram assistant with comprehensive knowledge of all Mermaid.js capabilities.
                Your only task is to help users create Mermaid diagrams based on their requirements, using the most appropriate diagram type (flowchart, sequence, timeline).
                You will generate valid Mermaid code wrapped in [MERMAID_START] and [MERMAID_END] tags, without using parentheses `()`.
                You will also provide explanations for your choices and suggest improvements or alternatives when appropriate.
                Your responses should be clear, concise, and focused on generating Mermaid diagrams that meet the user's needs.
                CRITICAL FORMATTING RULE: Use [MERMAID_START] and [MERMAID_END] tags, and avoid parentheses `()` in code, using square brackets `[]` or curly braces `{}` instead.
                ALWAYS generate Mermaid code for diagram requests, even if the request is ambiguous, by making reasonable assumptions.
            """,
            "flowchart_syntax": """
                ## FLOWCHART SYNTAX AND CAPABILITIES
                ### Basic Structure:
                - Start with: `flowchart TD` (top-down), `flowchart LR` (left-right), `flowchart BT` (bottom-top), `flowchart RL` (right-left)
                - Alternative: `graph TD` (same as flowchart)
                ### Node Shapes (30+ available):
                - **Rectangle**: `A[Text]` or `A@{ shape: rect }`
                - **Circle**: `A@{ shape: circle }`
                - **Diamond**: `A{Text}` or `A@{ shape: diam }` (for decisions)
                - **Stadium**: `A([Text])` or `A@{ shape: stadium }` (for start/end)
                - **Hexagon**: `A{{Text}}` or `A@{ shape: hex }` (for preparation)
                - **Cylinder**: `A[(Text)]` or `A@{ shape: cyl }` (for databases)
                - **Subroutine**: `A[[Text]]` or `A@{ shape: subprocess }`
                - **Trapezoid**: `A[/Text/]` or `A@{ shape: trapezoid }`
                - **Parallelogram**: `A[/Text\\]` or `A@{ shape: lean-r }`
                ### Advanced Shapes (v11.3.0+):
                - **Process**: `A@{ shape: process }`
                - **Decision**: `A@{ shape: decision }`
                - **Document**: `A@{ shape: doc }`
                - **Database**: `A@{ shape: database }`
                - **Start**: `A@{ shape: start }`
                - **Stop**: `A@{ shape: stop }`
                - **Manual Operation**: `A@{ shape: manual }`
                - **Delay**: `A@{ shape: delay }`
                - **Extract**: `A@{ shape: extract }`
                - **Junction**: `A@{ shape: junction }`
                ### Link Types:
                - **Arrow**: `A --> B`
                - **Open link**: `A --- B`
                - **Text on link**: `A -->|Text| B` or `A -- Text --> B`
                - **Dotted**: `A -.-> B` or `A -.- B`
                - **Thick**: `A ==> B` or `A === B`
                - **Invisible**: `A ~~~ B`
                - **Circle edge**: `A --o B`
                - **Cross edge**: `A --x B`
                - **Bidirectional**: `A <--> B`
                ### Link Length Control:
                - Longer links: `A -----> B` (more dashes)
                - For thick: `A =====> B`
                - For dotted: `A -...-> B`
                ### Subgraphs:
                subgraph Title
                    A --> B
                end
                ### Styling:
                - Node styling: `style A fill:#f9f,stroke:#333,stroke-width:4px`
                - Class definition: `classDef className fill:#f9f,stroke:#333`
                - Apply class: `class A className` or `A:::className`
            """,
            "sequence_syntax": """
                ## SEQUENCE DIAGRAM SYNTAX AND CAPABILITIES
                ### Basic Structure:
                sequenceDiagram
                    participant A as Alice
                    participant B as Bob
                    A->>B: Message
                ### Participants:
                - **Auto-defined**: Just use in messages
                - **Explicit**: `participant A as Alice`
                - **Actors**: `actor A as Alice` (shows person icon)
                - **Aliases**: `participant A as "Alice Smith"`
                ### Actor Creation/Destruction (v10.3.0+):
                create participant B
                A->>B: Hello
                destroy B
                ### Message Types:
                - **Solid arrow**: `A->>B: Message`
                - **Dotted arrow**: `A-->>B: Message`
                - **Solid line**: `A->B: Message`
                - **Dotted line**: `A-->B: Message`
                - **Bidirectional solid**: `A<<->>B: Message`
                - **Bidirectional dotted**: `A<<-->>B: Message`
                - **Cross ending**: `A-xB: Message`
                - **Open arrow**: `A-)B: Message` (async)
                ### Activations:
                - **Explicit**: `activate A` and `deactivate A`
                - **Shorthand**: `A->>+B: Message` (activate) and `B-->>-A: Response` (deactivate)
                - **Stacked**: Multiple activations on same actor
                ### Control Structures:
                - **Loop**: 
                loop Every minute
                    A->>B: Heartbeat
                end
                - **Alternative**:
                alt Success
                    A->>B: Success message
                else Failure
                    A->>B: Error message
                end
                - **Optional**:
                opt Extra security
                    A->>B: Encrypt message
                end
                - **Parallel**:
                par
                    A->>B: Message 1
                and
                    A->>C: Message 2
                end
                - **Critical**:
                critical Establish connection
                    A->>B: Connect
                option Network timeout
                    A->>A: Log timeout
                end
                - **Break**:
                break Something went wrong
                    A->>A: Log error
                end
                ### Notes:
                - **Right**: `Note right of A: Note text`
                - **Left**: `Note left of A: Note text`
                - **Over**: `Note over A: Note text`
                - **Spanning**: `Note over A,B: Note text`
                ### Background Highlighting:
                rect rgb(255, 255, 0)
                    A->>B: Important message
                end
                ### Grouping/Boxes:
                box Purple Alice & Bob
                    participant A
                    participant B
                end
            """,
            "timeline_syntax": """
                ## TIMELINE SYNTAX AND CAPABILITIES
                ### Basic Structure:
                timeline
                    title History of Social Media Platform
                    2002 : LinkedIn
                    2004 : Facebook
                         : Google
                    2005 : Youtube
                    2006 : Twitter
                ### Features:
                - **Title**: `title Timeline Title`
                - **Time periods**: Can be years, dates, or any time reference
                - **Multiple events**: Use `:` to separate events in same period
                - **Grouping**: Events under same time period are grouped
                - **Sections**: Can organize into sections for better structure
                ### Advanced Timeline:
                timeline
                    title Timeline of Industrial Revolution
                    section 18th Century
                        1712 : Steam Engine invented
                        1769 : Spinning Jenny invented
                        1779 : Crompton's Mule invented
                    section 19th Century
                        1804 : Steam locomotive invented
                        1825 : First passenger railway
                        1844 : Telegraph invented
            """,
            "conversation_rules": """
                ## CONVERSATION RULES:
                1. **Ask clarifying questions** to understand the user's specific needs
                2. **Suggest the most appropriate diagram type**:
                   - Flowcharts for processes, workflows, decision trees
                   - Sequence diagrams for interactions, API flows, communication
                   - Timeline for chronological events, project milestones, history
                3. **Generate valid syntax** wrapped in [MERMAID_START] and [MERMAID_END] tags
                4. **Use appropriate shapes and styles** for the context
                5. **Remember conversation context** for iterative improvements
                6. **Explain diagram choices** and offer alternatives
                ## BEST PRACTICES:
                - **Flowcharts**: Use diamonds for decisions, rectangles for processes, circles for start/end
                - **Sequence**: Keep participant names short, use meaningful message labels
                - **Timeline**: Use consistent time format, group related events
                - **All types**: Keep labels concise but descriptive
            """
        }

        # Initialize vector store
        self._initialize_vector_store()

    def _initialize_vector_store(self):
        """Add prompt chunks to the vector database if not already present."""
        existing_ids = self.collection.get()['ids']
        for chunk_id, chunk_content in self.prompt_chunks.items():
            if chunk_id not in existing_ids:
                self.collection.add(
                    documents=[chunk_content],
                    ids=[chunk_id],
                    metadatas=[{"type": chunk_id}]
                )

    def generate_response_with_context(self, session_id, user_message):
        """Generate contextual response with RAG"""
        try:
            # Get chat session
            session = ChatSession.objects.get(session_id=session_id)
            
            # Build conversation history
            messages = [{"role": "system", "content": self.prompt_chunks["general_instructions"]}]  # Always include general instructions
            
            # Add previous messages for context
            chat_history = ChatMessage.objects.filter(session=session).order_by('timestamp')
            for msg in chat_history:
                role = "user" if msg.message_type == "user" else "assistant"
                messages.append({"role": role, "content": msg.content})
            
            # Add current user message with explicit instruction to generate Mermaid code
            messages.append({"role": "user", "content": f"{user_message}\n\nGenerate a valid Mermaid diagram wrapped in [MERMAID_START] and [MERMAID_END] tags."})
            
            # Retrieve relevant prompt chunks using RAG
            relevant_chunks = self._retrieve_relevant_chunks(user_message, top_k=3)
            # Ensure general instructions and conversation rules are included
            system_prompt_chunks = [self.prompt_chunks["general_instructions"], self.prompt_chunks["conversation_rules"]]
            system_prompt_chunks.extend([chunk for chunk in relevant_chunks if chunk not in system_prompt_chunks])
            system_prompt = "\n".join(system_prompt_chunks)
            messages[0]["content"] = system_prompt
            
            # Log the system prompt and user message
            logger.debug(f"System prompt: {system_prompt}")
            logger.debug(f"User message: {user_message}")
            
            # Generate response
            headers = {
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost",
                "X-Title": "Mermaid Chat Assistant"
            }

            payload = {
                "model": "mistralai/mixtral-8x7b-instruct",  # Switched to a more capable model
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 6000  # Increased to ensure complete responses
            }

            response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            assistant_response = response.json()["choices"][0]["message"]["content"].strip()

            # Log the assistant response
            logger.debug(f"Assistant response: {assistant_response}")
            
            # Extract Mermaid code if present
            mermaid_code = self._extract_mermaid_code(assistant_response)
            
            # Validate Mermaid code
            if not mermaid_code:
                logger.warning(f"No Mermaid code extracted for user message: {user_message}")
                assistant_response += "\n\nNo diagram could be generated. Please provide more specific details or rephrase your request."
            
            # Save messages to database
            ChatMessage.objects.create(
                session=session,
                message_type='user',
                content=user_message
            )
            
            ChatMessage.objects.create(
                session=session,
                message_type='assistant',
                content=assistant_response,
                mermaid_code=mermaid_code
            )
            
            return {
                'success': True,
                'response': assistant_response,
                'mermaid_code': mermaid_code,
                'session_id': str(session_id)
            }
            
        except Exception as e:
            logger.error(f"Error in generate_response_with_context: {str(e)}")
            return {'error': str(e), 'success': False}

    def _retrieve_relevant_chunks(self, query, top_k=3):
        """Retrieve relevant prompt chunks from the vector database."""
        # Embed the user query
        query_embedding = self.embedder.encode(query, convert_to_tensor=False)
        
        # Query the vector database
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k
        )
        
        # Extract relevant documents
        relevant_chunks = [doc for doc in results['documents'][0]]
        logger.debug(f"Retrieved chunks: {relevant_chunks}")
        return relevant_chunks

    def _extract_mermaid_code(self, text):
        """Extract Mermaid code from assistant response"""
        start_tag = "[MERMAID_START]"
        end_tag = "[MERMAID_END]"
        
        if start_tag in text and end_tag in text:
            start_idx = text.find(start_tag) + len(start_tag)
            end_idx = text.find(end_tag)
            mermaid_code = text[start_idx:end_idx].strip()
            logger.debug(f"Extracted Mermaid code: {mermaid_code}")
            return mermaid_code
        
        return None

# Initialize the generator
mermaid_generator = ContextAwareMermaidGenerator()