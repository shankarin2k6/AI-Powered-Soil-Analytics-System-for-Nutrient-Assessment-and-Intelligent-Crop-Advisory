export default function PageHead({ title, lead }: { title: string; lead?: string }) {
  return (
    <div className="page-head">
      <h1>{title}</h1>
      {lead && <p className="lead">{lead}</p>}
    </div>
  );
}
