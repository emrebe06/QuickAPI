#ifndef QUICKAPI_POLICY_H
#define QUICKAPI_POLICY_H

#include "../core/quick_core.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum quickapi_policy_action {
    QUICKAPI_POLICY_ALLOW = 0,
    QUICKAPI_POLICY_OBSERVE = 1,
    QUICKAPI_POLICY_CHALLENGE = 2,
    QUICKAPI_POLICY_BLOCK = 3
} quickapi_policy_action;

QUICKAPI_EXPORT quickapi_policy_action quickapi_policy_decide(double risk_score, unsigned int security_flags, unsigned int route_sensitivity);
QUICKAPI_EXPORT const char* quickapi_policy_action_name(quickapi_policy_action action);
QUICKAPI_EXPORT const char* quickapi_policy_decision_json(double risk_score, unsigned int security_flags, unsigned int route_sensitivity);

#ifdef __cplusplus
}
#endif

#endif
