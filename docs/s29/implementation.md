# S29 Implementation Notes

## Contracts
- ActionType: ECHO, LOG (deliberately small)
- ActionState: REQUESTED → VALIDATED → AUTHORIZED → EXECUTING → SUCCEEDED/FAILED/UNKNOWN
- Terminal states: SUCCEEDED, FAILED, REJECTED, CANCELLED, UNKNOWN
- ActionOutcome: SUCCESS, FAILURE, REJECTION, UNKNOWN
- State-outcome consistency enforced in ActionResult.__post_init__
- MappingProxyType used to freeze parameters and metadata dicts

## Engine
- process() runs full lifecycle: validate → authorize → execute
- _validate(): checks action_type support and target presence
- _authorize(): constructs AuthorizationRequest, calls AuthorizerFn
- _execute(): dispatches to adapter, catches exceptions → FAILED
- Authorizer exceptions → DENY (fail-closed)

## Service
- Thin facade over engine
- execute(request, actor) entry point

## Capability
- Parses payload, constructs ActionRequest and ActorIdentity
- Delegates to service
- Returns ActionResult in Response.data

## No modifications to S23–S28 or Sx1
