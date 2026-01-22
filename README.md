# 🤖 Procurement AI Orchestrator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange)](https://github.com/langchain-ai/langgraph)

A multi-agent AI system that orchestrates complex procurement workflows with human-in-the-loop approvals, reducing cycle time by **60%**.

[📽️ Demo Video] | [🏗️ Architecture] | [🌐 Live Demo] | [📚 Documentation]

---

## 🎯 Problem Statement

Traditional procurement involves 6-8 manual handoffs across Finance, Legal, and Business units, leading to:

* **Inefficient Cycles:** 6+ day approval times (80% spent on coordination).
* **The "Black Box" Effect:** Stakeholders lack visibility into where requests are stalled.
* **Manual Drudgery:** High-paid talent spending hours matching invoices to Purchase Orders (POs).

## ✨ The Solution

An agentic AI system that acts as a **Digital PMO**, coordinating specialized agents to handle the "heavy lifting" while keeping humans in control.

> **Key Innovation:** Agents coordinate people and validate data; they do not replace human authority.

### Core Agent Capabilities
* **Prepare Decisions:** Risk scoring, invoice mismatch detection, and policy compliance.
* **Orchestrate Workflows:** Parallel approvals, automatic routing, and SLA tracking.
* **Maintain Integrity:** Full audit trails and state management via LangGraph.

---

## 🏗️ Architecture & Flow

The system uses a **Hybrid Orchestration** model: Deterministic rules handle routing, while AI Agents handle unstructured data and complex reasoning.

```mermaid
graph TB
    subgraph "User Layer"
        User[User Submits Request]
    end
    
    subgraph "Orchestration Layer - Rule-Based"
        Orchestrator[Workflow Orchestrator<br/>Rule Engine]
        
        subgraph "Rule-Based Validators"
            DepCheck[Dependency Validator]
            AmountRouter[Amount-Based Router]
            QtyValidator[Quantity Validator]
            StateEngine[State Machine]
        end
    end
    
    subgraph "AI Layer - Selective Use"
        VendorAgent[Vendor Risk Agent<br/>AI-Powered]
        SKUAgent[SKU Matching Agent<br/>AI-Powered]
        DocAgent[Document Processing Agent<br/>AI-Powered]
    end
    
    subgraph "Human Decision Layer"
        Parallel[Parallel Approvers]
        Finance[Finance Team]
        Legal[Legal Team]
        Business[Business Team]
    end
    
    subgraph "Data Layer"
        DB[(PostgreSQL)]
        S3[(AWS S3)]
    end
    
    User --> Orchestrator
    Orchestrator --> DepCheck
    Orchestrator --> AmountRouter
    Orchestrator --> QtyValidator
    Orchestrator --> StateEngine
    
    Orchestrator -.->|Only when needed| VendorAgent
    Orchestrator -.->|Only when needed| SKUAgent
    Orchestrator -.->|Only when needed| DocAgent
    
    Orchestrator --> Parallel
    Parallel --> Finance
    Parallel --> Legal
    Parallel --> Business
    
    Orchestrator --> DB
    Orchestrator --> S3
    
    style Orchestrator fill:#e1f5ff,stroke:#01579b,stroke-width:3px
    style VendorAgent fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style SKUAgent fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style DocAgent fill:#fff3e0,stroke:#e65100,stroke-width:2px