"""
Input and output guardrails for agent safety.
Author: Ben Walker (BenRWalker@icloud.com)
"""

import os
import re
from typing import List
from agents import input_guardrail, output_guardrail, GuardrailFunctionOutput
from logger_config import setup_logger

logger = setup_logger('guardrails', use_json=True)

# Security thresholds
RISK_THRESHOLD = float(os.environ.get('RISK_THRESHOLD', '0.75'))
TOXICITY_THRESHOLD = float(os.environ.get('TOXICITY_THRESHOLD', '0.8'))

# Regex patterns for prompt injection
PROMPT_INJECTION_PATTERNS = [
    r'ignore\s+all\s+previous\s+instructions',
    r'forget\s+your\s+role',
    r'you\s+are\s+now\s+a',
    r'<\|im_start\|>system',
    r'\[INST\].*ignore',
]

# PII patterns
PII_PATTERNS = [
    r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
    r'\b\d{16}\b',  # Credit card
    r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
]


def heuristic_injection_check(text: str) -> tuple[bool, List[str]]:
    """Check for obvious prompt injection patterns"""
    detected_patterns = []
    text_lower = text.lower()
    
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text_lower):
            detected_patterns.append(pattern)
            logger.warning(f"Injection pattern detected: {pattern}")
    
    return len(detected_patterns) > 0, detected_patterns


def heuristic_pii_check(text: str) -> tuple[bool, List[str], float]:
    """Check for PII"""
    detected_pii = []
    
    for pattern in PII_PATTERNS:
        if re.search(pattern, text):
            detected_pii.append(pattern)
            logger.warning(f"PII pattern detected: {pattern}")
    
    confidence = min(1.0, len(detected_pii) * 0.3) if detected_pii else 0.0
    return len(detected_pii) > 0, detected_pii, confidence


@input_guardrail
async def comprehensive_input_guardrail(ctx, agent, message):
    """Simple input guardrail - only blocks obvious attacks"""
    logger.info(f"Running input guardrail on message length: {len(message)}")
    
    # Check for prompt injection
    has_injection, injection_issues = heuristic_injection_check(message)
    
    if has_injection:
        logger.error(f"Input blocked - prompt injection detected: {injection_issues}")
        return GuardrailFunctionOutput(
            output_info={
                "blocked": True,
                "reason": "Prompt injection pattern detected",
                "issues": injection_issues
            },
            tripwire_triggered=True
        )
    
    # Check for PII
    has_pii, pii_issues, pii_confidence = heuristic_pii_check(message)
    
    if has_pii and pii_confidence > 0.7:
        logger.warning(f"PII detected: {pii_issues}")
        return GuardrailFunctionOutput(
            output_info={
                "blocked": True,
                "reason": "PII detected in input",
                "issues": pii_issues,
                "confidence": pii_confidence
            },
            tripwire_triggered=True
        )
    
    # Passed guardrail
    logger.info("Input passed guardrail checks")
    return GuardrailFunctionOutput(
        output_info={"blocked": False, "issues": []},
        tripwire_triggered=False
    )


@output_guardrail
async def comprehensive_output_guardrail(ctx, agent, output):
    """Simple output guardrail - only blocks actual data leaks"""
    logger.info(f"Running output guardrail on output length: {len(str(output))}")
    
    output_text = str(output)
    
    # Check for API keys or passwords
    leak_patterns = [
        r'api[_-]?key[:=]\s*["\']?[^\s"\'\n]+',
        r'password[:=]\s*["\']?[^\s"\'\n]+',
    ]
    
    detected_leaks = []
    for pattern in leak_patterns:
        if re.search(pattern, output_text, re.IGNORECASE):
            detected_leaks.append(pattern)
            logger.error(f"Potential data leak detected: {pattern}")
    
    if detected_leaks:
        logger.error(f"Output blocked - {len(detected_leaks)} leak patterns detected")
        return GuardrailFunctionOutput(
            output_info={
                "blocked": True,
                "reason": "Potential data leak detected",
                "leaks": detected_leaks
            },
            tripwire_triggered=True
        )
    
    # Passed guardrail
    logger.info("Output passed guardrail checks")
    return GuardrailFunctionOutput(
        output_info={"blocked": False, "leaks": []},
        tripwire_triggered=False
    )
