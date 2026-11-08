import "./visual-guide.css";
const guides: Record<string, [string, string, string]> = {
 overview: ["portfolio", "See risk. Choose your next move.", "Select a building on the map, or open Fix-First to compare actions and potential savings."],
 buildings: ["portfolio", "Start with a property", "Choose a building to see its hazards, estimated loss, and response options."],
 building: ["portfolio", "Turn this assessment into action", "Review the modeled impact below, then approve a plan or prepare a tenant notice."],
 fixfirst: ["response", "Put the highest-impact actions first", "Compare cost, potential savings, and deadlines. Approval creates trackable work orders."],
 workorders: ["response", "Follow the work through to completion", "Open a task to update its status. Add a note when work is blocked so the team can respond."],
 help: ["community", "Connect people with available help", "Check site safety and available places, then review resident requests or activate an eligible site."],
 messages: ["messages", "Keep every conversation in view", "Review delivery status and replies. Use the simulator to rehearse a technician update or resident request."],
 reports: ["reports", "Share a clear next step", "Create a printable summary or tenant notice using the current scenario and approved actions."],
};
/** Original illustrations explain workflows; they are not incident evidence. */
export default function VisualGuide({ view }: { view: string }) {
 const guide = guides[view]; if (!guide) return null;
 const [image, title, description] = guide;
 return <div className="visual-guide"><img src={`/illustrations/${image}.svg`} alt="" aria-hidden="true" width="240" height="160" /><div><p className="visual-guide-title">{title}</p><p>{description}</p></div></div>;
}
