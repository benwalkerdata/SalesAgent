"""
Input and output guardrails for agent safety.
Author: Ben Walker (BenRWalker@icloud.com)
"""

from agents import Runner, input_guardrail, output_guardrail, GuardrailFunctionOutput
from agent_setup import guardrail_agent, input_guardrail_agent, output_guardrail_agent
from logger_config import setup_logger
import re
from typing import List

# Set up logger for guardrails
logger = setup_logger('guardrails', use_json=True)

# Regex patterns for ACTUAL attack patterns (narrowed down)
PROMPT_INJECTION_PATTERNS = [
    r'ignore\s+all\s+previous\s+instructions',  # More specific
    r'forget\s+your\s+role',  # More specific
    r'you\s+are\s+now\s+a',  # More specific
    r'<\|im_start\|>system',  # Actual system override
    r'\[INST\].*ignore',  # Actual instruction injection
]

# Sensitive data patterns (keep these)
PII_PATTERNS = [
    r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
    r'\b\d{16}\b',  # Credit card
    r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone number
]


def heuristic_injection_check(text: str) -> tuple[bool, List[str]]:
    """Fast heuristic check for OBVIOUS prompt injection patterns"""
    detected_patterns = []
    text_lower = text.lower()
    
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text_lower):
            detected_patterns.append(f"Detected pattern: {pattern}")
            logger.warning(
                "Prompt injection pattern detected",
                extra={
                    'pattern': pattern,
                    'input_preview': text[:100]
                }
            )
    
    return len(detected_patterns) > 0, detected_patterns


def heuristic_pii_check(text: str) -> tuple[bool, List[str]]:
    """Fast heuristic check for PII"""
    detected_pii = []
    
    for pattern in PII_PATTERNS:
        matches = re.findall(pattern, text)
        if matches:
            detected_pii.append(f"Found PII matching pattern: {pattern}")
            logger.warning(
                "PII detected in input",
                extra={
                    'pattern': pattern,
                    'match_count': len(matches)
                }
            )
    
    return len(detected_pii) > 0, detected_pii


@input_guardrail
async def comprehensive_input_guardrail(ctx, agent, message):
    """
    Relaxed input guardrail - only blocks OBVIOUS attacks
    """
    logger.info(
        "Running input guardrail",
        extra={
            'message_length': len(message),
            'agent_name': agent.name if hasattr(agent, 'name') else 'unknown'
        }
    )
    
    issues = []
    
    # Fast heuristic checks first
    has_injection, injection_issues = heuristic_injection_check(message)
    has_pii, pii_issues = heuristic_pii_check(message)
    
    if has_injection:
        issues.extend(injection_issues)
        logger.warning("Injection patterns found", extra={'issues': injection_issues})
    if has_pii:
        issues.extend(pii_issues)
        logger.warning("PII found", extra={'issues': pii_issues})
    
    # ONLY block if MULTIPLE obvious injection patterns (not just one)
    if has_injection and len(injection_issues) > 1:  # Changed from > 2 to > 1
        logger.error(
            "Input blocked - multiple prompt injection patterns",
            extra={
                'issue_count': len(injection_issues),
                'issues': issues
            }
        )
        return GuardrailFunctionOutput(
            output_info={
                "blocked": True,
                "reason": "Multiple prompt injection patterns detected",
                "issues": issues
            },
            tripwire_triggered=True
        )
    
    # Skip LLM guardrail for sales email requests
    # Only run LLM check if heuristics found something suspicious
    if has_injection or has_pii:
        logger.debug("Running LLM-based guardrail check (heuristics triggered)")
        result = await Runner.run(input_guardrail_agent, message, context=ctx.context)
        guardrail_output = result.final_output
        
        # Combine results
        all_issues = issues + guardrail_output.flagged_issues
        
        # MUCH higher threshold - only block EXTREME cases
        should_block = (
            not guardrail_output.is_safe and
            guardrail_output.risk_score > 0.9 and  # Changed from 0.7 to 0.9
            guardrail_output.is_prompt_injection
        )
    else:
        # No heuristic issues - skip LLM check entirely
        logger.info("No heuristic issues - skipping LLM guardrail check")
        should_block = False
        all_issues = issues
        guardrail_output = None
    
    if should_block:
        logger.error(
            "Input blocked by guardrail",
            extra={
                'risk_score': guardrail_output.risk_score if guardrail_output else 0,
                'all_issues': all_issues
            }
        )
    else:
        logger.info(
            "Input passed guardrail",
            extra={
                'risk_score': guardrail_output.risk_score if guardrail_output else 0
            }
        )
    
    return GuardrailFunctionOutput(
        output_info={
            "guardrail_result": guardrail_output,
            "heuristic_issues": issues,
            "all_issues": all_issues,
            "risk_score": guardrail_output.risk_score if guardrail_output else 0
        },
        tripwire_triggered=should_block
    )


@output_guardrail
async def comprehensive_output_guardrail(ctx, agent, output):
    """
    Relaxed output guardrail - only blocks REAL problems
    """
    logger.info(
        "Running output guardrail",
        extra={
            'output_length': len(str(output)),
            'agent_name': agent.name if hasattr(agent, 'name') else 'unknown'
        }
    )
    
    output_text = str(output)
    
    # Check for ACTUAL data leaks (not normal sales content)
    leak_patterns = [
        r'api[_-]?key[:=]\s*["\']?sk-[\w-]+["\']?',  # More specific - actual API keys
        r'password[:=]\s*["\']?[\w]{12,}["\']?',  # More specific - actual passwords
        r'secret[:=]\s*["\']?[\w-]{20,}["\']?',  # More specific - actual secrets
    ]
    
    detected_leaks = []
    for pattern in leak_patterns:
        if re.search(pattern, output_text, re.IGNORECASE):
            detected_leaks.append(pattern)
            logger.warning(
                "Potential data leak detected",
                extra={'pattern': pattern}
            )
    
    # Skip LLM output check for performance - only do if leaks detected
    if detected_leaks:
        logger.debug("Running LLM-based output guardrail check (leak detected)")
        result = await Runner.run(output_guardrail_agent, output_text, context=ctx.context)
        guardrail_output = result.final_output
        
        should_block = (
            not guardrail_output.is_safe or
            guardrail_output.contains_sensitive_data or
            guardrail_output.toxicity_score > 0.9 or  # Changed from 0.8 to 0.9
            len(detected_leaks) > 0
        )
    else:
        # No leaks - skip LLM check
        logger.info("No output leaks detected - skipping LLM guardrail check")
        should_block = False
        guardrail_output = None
    
    final_output = output
    if guardrail_output and guardrail_output.contains_sensitive_data and guardrail_output.redacted_output:
        final_output = guardrail_output.redacted_output
        logger.info("Output redacted due to sensitive data")
    
    if should_block:
        logger.error(
            "Output blocked by guardrail",
            extra={
                'toxicity_score': guardrail_output.toxicity_score if guardrail_output else 0,
                'detected_leaks': detected_leaks
            }
        )
    else:
        logger.info(
            "Output passed guardrail",
            extra={
                'toxicity_score': guardrail_output.toxicity_score if guardrail_output else 0
            }
        )
    
    return GuardrailFunctionOutput(
        output_info={
            "guardrail_result": guardrail_output,
            "detected_leaks": detected_leaks,
            "toxicity_score": guardrail_output.toxicity_score if guardrail_output else 0,
            "final_output": final_output
        },
        tripwire_triggered=should_block
    )


# Legacy guardrail for backward compatibility
@input_guardrail
async def guardrail_against_name(ctx, agent, message):
    """Check if user message contains personal names and is professional."""
    logger.debug("Running name check guardrail")
    
    result = await Runner.run(guardrail_agent, message, context=ctx.context)
    is_name_in_message = result.final_output.is_name_in_message
    
    if is_name_in_message:
        logger.warning(
            "Name detected in message",
            extra={'name': result.final_output.name}
        )
    
    # Don't block on name detection - just log it
    return GuardrailFunctionOutput(
        output_info={"found_name": result.final_output},
        tripwire_triggered=False  # Changed from is_name_in_message to False
    )
